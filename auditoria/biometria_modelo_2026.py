"""Análise ecológica nacional 2026: biometria agregada e votos presidenciais.

Modelo A: associação bruta entre proporção de identificações sem habilitação
biométrica e participação de votos 13 entre válidos, ponderada pelos válidos.

Modelo B: mínimos quadrados com efeitos fixos de município; ponderação
pelos votos válidos e erros padrão agrupados por município.
Modelo C: acrescenta comparecimento/aptos e log(aptos).
Sensibilidade: sem pesos; setores com >=100 votos válidos; corte nas taxas
acima de 99º percentil. Nenhum modelo conclui fraude ou causalidade.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime,timezone
import gzip
import json
from math import log
from pathlib import Path

import numpy as np

from .tse import UFS

def read_data(folder):
    data=[]
    summaries={}
    errors=[]
    for uf in UFS:
        p=Path(folder)/(uf+".json")
        f=Path(folder)/(uf+".csv.gz")
        if not p.exists() or not f.exists():
            errors.append(f"{uf}: arquivo ausente")
            continue
        try:
            d=json.loads(p.read_text(encoding="utf-8"))
            if d["uf"]!=uf or d["status"]!="OK":
                errors.append(f"{uf}: status {d.get('status')}")
                continue
            summaries[uf]=d
            seen=0
            with gzip.open(f,"rt",encoding="utf-8",newline="") as stream:
                for row in csv.DictReader(stream):
                    if row["uf"]!=uf:raise ValueError("UF incompatível")
                    expected=int(row["votos_13"])+int(row["votos_22"])
                    if expected!=int(row["votos_validos"]):
                        raise ValueError("Votos válidos inconsistentes")
                    comp=int(row["comparecimento"])
                    biometric=int(row["sem_biometria"])
                    aptos=int(row["aptos"])
                    if not 0<=biometric<=comp<=aptos:
                        raise ValueError("Identificação alternativa, comparecimento ou aptos inválidos")
                    seen+=1
                    if comp<=0 or expected<=0 or aptos<=0:
                        continue
                    data.append((uf, int(row["municipio"]),
                                 biometric/comp,int(row["votos_13"])/expected,
                                 comp/aptos, float(log(aptos)), expected,
                                 biometric,comp))
            if seen!=d["cobertura"]["secoes_exportadas"]:
                raise ValueError(f"{uf}: linhas {seen}, esperado {d['cobertura']['secoes_exportadas']}")
        except Exception as exc:
            errors.append(f"{uf}: {type(exc).__name__}: {exc}")
    return data,summaries,errors


def weighted_corr(a,b,w):
    if not len(a):return None
    norm=float(w.sum())
    if norm<=0:return None
    ma=float((a*w).sum()/norm)
    mb=float((b*w).sum()/norm)
    va=float((w*(a-ma)**2).sum()/norm)
    vb=float((w*(b-mb)**2).sum()/norm)
    if va<=1e-20 or vb<=1e-20:return None
    cov=float((w*(a-ma)*(b-mb)).sum()/norm)
    return cov/(va*vb)**0.5


def prepare(rows,min_votes=1,trim_quantile=None,weighted=True):
    if not rows:raise ValueError("Sem seções")
    a=[r for r in rows if r[6]>=min_votes]
    if not a:raise ValueError("Sem seções válidas após filtro")
    if trim_quantile is not None:
        ceiling=float(np.quantile([r[2] for r in a],trim_quantile))
        a=[r for r in a if r[2]<=ceiling]
    group_names=[f"{r[0]}:{r[1]}" for r in a]
    groups,inv=np.unique(group_names,return_inverse=True)
    x=np.array([r[2] for r in a],dtype=np.float64)
    y=np.array([r[3] for r in a],dtype=np.float64)
    turn=np.array([r[4] for r in a],dtype=np.float64)
    size=np.array([r[5] for r in a],dtype=np.float64)
    w=np.array([r[6] if weighted else 1 for r in a],dtype=np.float64)
    return a,groups,inv,np.column_stack((x,turn,size)),y,w


def municipality_fe(rows,controls=False,min_votes=1,weighted=True,trim_quantile=None):
    """Mínimos quadrados within e covariância robusta a cluster do município."""
    data,groups,inv,matrix,y,w=prepare(rows,min_votes,trim_quantile,weighted)
    N=len(y); G=len(groups)
    group_n=np.bincount(inv,minlength=G)
    # Remove municipalidades com uma seção, pois não há variação within.
    take=group_n[inv]>=2
    x=matrix[take,:3 if controls else 1]
    y=y[take];w=w[take];inv=inv[take]
    N=len(y)
    if N<100 or len(np.unique(inv))<20:
        return {"status":"AMOSTRA_INSUFICIENTE","n":N,"municipios":len(np.unique(inv))}
    G=len(groups)
    group_w=np.bincount(inv,weights=w,minlength=G)
    x_mean=np.column_stack([
        np.bincount(inv,weights=w*x[:,j],minlength=G)/np.maximum(group_w,1)
        for j in range(x.shape[1])
    ])
    y_mean=np.bincount(inv,weights=w*y,minlength=G)/np.maximum(group_w,1)
    xx=x-x_mean[inv]
    yy=y-y_mean[inv]
    Xw=xx*np.sqrt(w)[:,None]
    yw=yy*np.sqrt(w)
    rank=int(np.linalg.matrix_rank(Xw))
    k=xx.shape[1]
    if rank!=k:
        return {"status":"COLINEARIDADE","n":N,"colunas":k,"rank":rank}
    gram=Xw.T@Xw
    inv_gram=np.linalg.inv(gram)
    betas=inv_gram@(Xw.T@yw)
    residual=yy-xx@betas
    # SE de cluster agrupado por UF+município (covariância sanduíche CR1).
    score=np.zeros((G,k))
    for j in range(k):
        score[:,j]=np.bincount(
            inv,weights=w*xx[:,j]*residual,minlength=G
        )
    Gused=int((group_w>0).sum())
    meat=score.T@score
    cov=inv_gram@meat@inv_gram
    if Gused>1 and N>k:
        cov*=Gused/(Gused-1)*(N-1)/(N-k)
    se=np.sqrt(np.maximum(np.diag(cov),0))
    explained=float(((xx@betas)**2*w).sum())
    total=float((yy**2*w).sum())
    beta=float(betas[0])
    stderr=float(se[0])
    return {
        "status":"EXECUTADO",
        "n":N,"municipios":Gused,"variaveis":["taxa_sem_habilitacao_biometrica"]+
            (["taxa_comparecimento","log_aptos"] if controls else []),
        "coeficientes":[float(v) for v in betas],
        "erros_padrao_cluster":[float(v) for v in se],
        "efeito_estimado_por_10pp_maior_taxa_sem_biometria_em_pp_voto_13":beta*10,
        "intervalo_95pp_em_pontos_percentuais":[
            (beta-1.96*stderr)*10,(beta+1.96*stderr)*10
        ],
        "correlacao_within_ponderada":weighted_corr(xx[:,0],yy,w),
        "r2_within":explained/total if total>0 else None,
        "observacao":"Estimativa associativa, não efeito causal. Erros padrão agrupados por município."
    }


def report_model(rows,descriptions):
    if not rows:raise ValueError("Sem dados")
    x=np.array([r[2] for r in rows])
    y=np.array([r[3] for r in rows])
    w=np.array([r[6] for r in rows],dtype=float)
    nonbio=sum(r[7] for r in rows)
    comparecimento=sum(r[8] for r in rows)
    result={
        "gerado_utc":datetime.now(timezone.utc).isoformat(),
        "projeto":"FATOVIA AUDITA",
        "ano":2026,"turno":2,"escopo":"2º turno presidencial",
        "status":"EXECUTADO_COM_RESSALVAS",
        "descricao":descriptions,
        "total":{
            "secoes_validas_para_correlacao":len(rows),
            "identificacoes_sem_habilitacao_biometrica":nonbio,
            "comparecimento":comparecimento,
            "taxa_nacional_ponderada_por_comparecimento":(
                nonbio/comparecimento if comparecimento else None),
            "correlacao_bruta_ponderada_pelos_votos_validos":weighted_corr(x,y,w),
            "media_ponderada_participacao_votos_13":float(np.average(y,weights=w)),
        },
        "modelos":{
            "municipio_fe":municipality_fe(rows),
            "municipio_fe_mais_controles":municipality_fe(rows,controls=True),
            "sensibilidade_sem_pesos":municipality_fe(rows,controls=True,weighted=False),
            "sensibilidade_100_validos_min":municipality_fe(rows,controls=True,min_votes=100),
            "sensibilidade_corte_cauda_99percentil":municipality_fe(
                rows,controls=True,trim_quantile=0.99),
        },
        "por_uf":{},
        "limitacoes":[
            "Associação ecológica, não causalidade, prova de fraude, ou voto individual.",
            "A taxa é a razão QT_ELEI_BIOM_SEM_HABILITACAO / QT_COMPARECIMENTO, agregada UMA vez por seção.",
            "A participação é votos 13 / (votos 13 + votos 22), não o total de comparecimento.",
            "Efeitos fixos municipais só comparam seções do MESMO município.",
            "O modelo ajustado inclui taxa de comparecimento e log(aptos), mas fatores sociais, demográficos e operacionais não observados persistem.",
            "Erros padrão com clusters municipais não resolvem confundimento.",
            "Unidade exterior (ZZ) tratada separadamente; relatório nacional exclui ZZ da regressão principal por diferenças de contexto.",
            "Não é possível atribuir a candidatura escolhida a eleitor identificado sem biometria.",
        ]
    }
    byuf={}
    for row in rows:
        byuf.setdefault(row[0],[]).append(row)
    for uf,rs in sorted(byuf.items()):
        outcome={
            "secoes":len(rs),
            "identificacoes_sem_biometria":sum(r[7] for r in rs),
            "comparecimento":sum(r[8] for r in rs),
            "correlacao_bruta_ponderada":weighted_corr(
                np.array([r[2] for r in rs]),
                np.array([r[3] for r in rs]),
                np.array([r[6] for r in rs],dtype=float)),
            "modelo_ajustado":municipality_fe(rs,controls=True),
        }
        outcome["taxa_sem_biometria"]=(
            outcome["identificacoes_sem_biometria"]/outcome["comparecimento"]
            if outcome["comparecimento"] else None
        )
        result["por_uf"][uf]=outcome
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="work/biometria")
    p.add_argument("--out",default="work/biometria-consolidado")
    a=p.parse_args()
    dest=Path(a.out);dest.mkdir(parents=True,exist_ok=True)
    rows,inputs,errors=read_data(a.input)
    domestic=[r for r in rows if r[0]!="ZZ"]
    summary={"fontes":{k:{"sha512":d["fontes"]["sha512"],
                          "secoes":d["cobertura"]["secoes_exportadas"],
                          "totais":d["totais"]} for k,d in inputs.items()},
             "ufs_incorporadas":sorted(inputs),
             "ufs_ausentes_ou_invalidas":errors,
             "quantidade_ufs":len(inputs),
             "exterior_incluido_na_contagem_nacional":False,
             "observacao":"Regressão principal exclui ZZ; informações do exterior ficam nos arquivos por UF."}
    if not errors and len(inputs)==len(UFS):
        result=report_model(domestic,summary)
    else:
        result={"status":"INCONCLUSIVO","descricao":summary,
                "erros":errors,"parcial_nao_publicar_como_nacional":True,
                "por_uf":{}}
    filename=dest/"biometria-2026-2t-nacional.json"
    filename.write_text(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    lines=["# FATOVIA AUDITA | Identificação biométrica e voto por seção | 2026",
           "",f"**Status: {result['status']}**",
           "",f"**UFs incorporadas:** {len(inputs)}/{len(UFS)}",
           "",f"**Unidades pendentes:** {', '.join(errors) if errors else 'nenhuma'}",
           ""]
    if result["status"]!="INCONCLUSIVO":
        tot=result["total"]
        lines.extend([
           f"- Seções válidas (Brasil sem exterior): **{tot['secoes_validas_para_correlacao']:,}**.",
           f"- Habilitações sem biometria: **{tot['identificacoes_sem_habilitacao_biometrica']:,}** (não significa votos irregulares).",
           f"- Taxa sobre comparecimento: **{tot['taxa_nacional_ponderada_por_comparecimento']:.4%}**.",
           f"- Associação bruta ponderada: **{tot['correlacao_bruta_ponderada_pelos_votos_validos']:.5f}**.",
           "", "## Estimativas por 10 pontos percentuais de taxa de identificação sem biometria", "",
           "| Modelo | n seções | Municípios | Estimativa em pp | IC95% (pp) |",
           "|---|---:|---:|---:|---|"
        ])
        for name,d in result["modelos"].items():
            if d.get("status")!="EXECUTADO":
                lines.append(f"| {name} | - | - | Não estimável | - |")
                continue
            effect=d["efeito_estimado_por_10pp_maior_taxa_sem_biometria_em_pp_voto_13"]
            ci=d["intervalo_95pp_em_pontos_percentuais"]
            lines.append(f"| {name} | {d['n']:,} | {d['municipios']:,} | {effect:+.3f} | [{ci[0]:+.3f}, {ci[1]:+.3f}] |")
        lines.extend(["", "## UFs", "",
                      "| UF | Seções | Taxa sem biometria | Associação ajustada (pp por +10pp) |",
                      "|---|---:|---:|---:|"])
        for uf,d in sorted(result["por_uf"].items()):
            effect=d["modelo_ajustado"].get("efeito_estimado_por_10pp_maior_taxa_sem_biometria_em_pp_voto_13")
            val=f"{effect:+.3f}" if effect is not None else "Não estimável"
            lines.append(f"| {uf} | {d['secoes']:,} | {d['taxa_sem_biometria']:.3%} | {val} |")
    lines.extend(["","## Limitações", "",
        "- Trata-se de inferência ecológica. Não existe vínculo entre votos individuais e identificação biométrica.",
        "- Nem uma associação estatística nem sua ausência provam ou descartam fraude.",
        "- O modelo controla diferenças fixas entre municípios e tamanho/comparecimento de seções; não controla todos os fatores de confusão.",
        "- Os dados foram validados por hash e são publicados pelo TSE. Não há auditoria de identificação pessoal.",
        "- Arquivos por UF estão nos artefatos da execução do GitHub Actions.",
        ""])
    (dest/"biometria-2026-2t-nacional.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({"status":result["status"],"ufs":len(inputs),
        "secoes":result.get("total",{}).get("secoes_validas_para_correlacao"),
        "taxa":result.get("total",{}).get("taxa_nacional_ponderada_por_comparecimento"),
        "correlacao_bruta":result.get("total",{}).get("correlacao_bruta_ponderada_pelos_votos_validos"),
        "modelo":result.get("modelos",{}).get("municipio_fe_mais_controles"),
        "erros":errors},ensure_ascii=False),flush=True)
    if errors:raise SystemExit(2)

if __name__=="__main__":
    main()
