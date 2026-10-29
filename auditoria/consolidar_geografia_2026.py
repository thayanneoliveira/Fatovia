"""Consolida seções e urnas por município e localiza alertas técnicos históricos.

Não geocodifica endereços, não identifica pessoas, não atribui voto individual
à identificação biométrica. Código eleitoral de município não é código IBGE.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import argparse,csv,gzip,json
from .tse import UFS

def number(r,k):
    value=str(r[k]).strip()
    if not value.isascii() or not value.isdigit():
        raise ValueError(f"Campo numérico inválido: {k}")
    return int(value)

def run(input_dir,original_dir,out_dir):
    input_dir,original_dir,out_dir=map(Path,(input_dir,original_dir,out_dir))
    out_dir.mkdir(parents=True,exist_ok=True)
    names={}
    cities={}
    per_uf={}
    errs=[]
    original_alerts=[]
    total=0
    with gzip.open(out_dir/"urnas-secoes-2026-2t.csv.gz","wt",encoding="utf-8",newline="") as dest:
        writer=None
        for uf in UFS:
            csvfile=input_dir/(uf+".csv.gz")
            jsonfile=input_dir/(uf+".json")
            if not csvfile.exists() or not jsonfile.exists():
                errs.append(f"{uf}: fonte ausente")
                continue
            info=json.loads(jsonfile.read_text(encoding="utf-8"))
            if info["status"] not in ("OK","ALERTAS_DE_COBERTURA"):
                errs.append(f"{uf}: extracao inconclusiva")
                continue
            with gzip.open(csvfile,"rt",encoding="utf-8",newline="") as src:
                reader=csv.DictReader(src)
                if writer is None:
                    writer=csv.DictWriter(dest,fieldnames=reader.fieldnames)
                    writer.writeheader()
                elif reader.fieldnames!=writer.fieldnames:
                    raise ValueError(f"Colunas divergentes em {uf}")
                n=0
                for r in reader:
                    if r["uf"]!=uf:raise ValueError("UF divergente")
                    code=number(r,"cod_municipio_tse")
                    key=(uf,code)
                    name=r["nome_municipio"]
                    if not name:raise ValueError("Nome de município vazio")
                    if key in names and names[key]!=name:
                        raise ValueError("Código município associado a nomes conflitantes")
                    names[key]=name
                    writer.writerow(r)
                    city=cities.setdefault(key,{
                        "uf":uf,"cod_municipio_tse":code,"nome_municipio":name,
                        "secoes":0,"aptos":0,"comparecimento":0,"sem_biometria":0,
                        "votos_13":0,"votos_22":0,"brancos":0,"nulos":0,
                        "urnas_substituidas":0,"urnas_distintas":set(),
                        "_n":0,"_sum_rate":0.0,"_sum_rate_sq":0.0,
                    })
                    city["secoes"]+=1
                    for k in ("aptos","comparecimento","sem_biometria","votos_13",
                              "votos_22","brancos","nulos"):
                        city[k]+=number(r,k)
                    city["urnas_substituidas"]+=number(r,"urna_substituida")
                    if r["urna_efetivada"]:
                        city["urnas_distintas"].add(r["urna_efetivada"])
                    aptos=number(r,"aptos")
                    if aptos:
                        rate=number(r,"comparecimento")/aptos
                        city["_n"]+=1
                        city["_sum_rate"]+=rate
                        city["_sum_rate_sq"]+=rate*rate
                    n+=1
            if n!=info["contagens"]["secoes_bu"]:
                raise ValueError(f"{uf}: falta de cobertura: {n}")
            per_uf[uf]={"secoes":n,
                       "municipios":info["contagens"]["municipios_distintos"],
                       "secoes_ceft":info["contagens"]["secoes_ceft"],
                       "ceft_sem_bu":info["contagens"]["secoes_ceft_sem_bu"],
                       "urnas_substituidas":info["contagens"]["urnas_prevista_diferente_efetivada"],
                       "hash_bu":info["fontes"]["BU"]["sha512"],
                       "hash_ceft":info["fontes"]["CEFT"]["sha512"],
                       "status":info["status"]}
            total+=n
    fields=("uf","cod_municipio_tse","nome_municipio","secoes","aptos",
            "comparecimento","abstencoes","sem_biometria","taxa_comparecimento",
            "taxa_sem_biometria","votos_13","votos_22","brancos","nulos",
            "urnas_substituidas","urnas_efetivadas_distintas",
            "desvio_padrao_taxa_comparecimento_por_secao")
    with gzip.open(out_dir/"municipios-2026-2t.csv.gz","wt",encoding="utf-8",newline="") as out:
        w=csv.DictWriter(out,fieldnames=fields);w.writeheader()
        for key,c in sorted(cities.items()):
            att=c["comparecimento"];apt=c["aptos"];n=c["_n"]
            mean=c["_sum_rate"]/n if n else 0
            sd=max(0,c["_sum_rate_sq"]/n-mean**2)**0.5 if n else 0
            row={k:c[k] for k in ("uf","cod_municipio_tse","nome_municipio","secoes",
                  "aptos","comparecimento","sem_biometria","votos_13","votos_22",
                  "brancos","nulos","urnas_substituidas")}
            row.update({
                "abstencoes":apt-att,
                "taxa_comparecimento":f"{att/apt:.10f}" if apt else "",
                "taxa_sem_biometria":f"{c['sem_biometria']/att:.10f}" if att else "",
                "urnas_efetivadas_distintas":len(c["urnas_distintas"]),
                "desvio_padrao_taxa_comparecimento_por_secao":f"{sd:.10f}",
            })
            w.writerow(row)
    for uf in UFS:
        path=original_dir/(uf+".json")
        if not path.exists():
            errs.append(f"{uf}: histórico de alertas não encontrado")
            continue
        d=json.loads(path.read_text(encoding="utf-8"))
        for section,detail in d.get("resultado_por_secao",{}).items():
            key=tuple(map(int,section.split("/")))
            for kind in detail.get("alertas",[]):
                original_alerts.append({
                    "uf":uf,"cod_municipio_tse":key[0],
                    "nome_municipio":names.get((uf,key[0]),"NAO_LOCALIZADO"),
                    "zona":key[1],"secao":key[2],"tipo_alerta":kind,
                    "resultado_novo":"FALHA_REDE_REPROCESSADA" if kind=="EXCECAO_AUDITORIA_SECAO" else "AGUARDA_INTERPRETACAO",
                })
    with (out_dir/"ocorrencias-cidades-2026-2t.csv").open("w",encoding="utf-8",newline="") as out:
        fields_alert=("uf","cod_municipio_tse","nome_municipio","zona","secao",
                      "tipo_alerta","resultado_novo")
        w=csv.DictWriter(out,fieldnames=fields_alert);w.writeheader()
        w.writerows(sorted(original_alerts,key=lambda a:(a["uf"],a["cod_municipio_tse"],a["zona"],a["secao"])))
    state="OK" if not errs and len(per_uf)==len(UFS) else "INCONCLUSIVO"
    report={
        "status":state,"gerado_utc":datetime.now(timezone.utc).isoformat(),
        "unidades_geograficas":len(per_uf),
        "secoes_bu":total,"municipios_distintos_por_uf":len(cities),
        "alertas_historicos_georreferenciados_por_nome":len(original_alerts),
        "por_uf":per_uf,"falhas":errs,
        "limitacoes":[
            "Código de município é código TSE; localização não possui coordenadas nem código IBGE.",
            "Cidade representa município da seção, não endereço preciso da urna.",
            "Duas entradas CEFT no exterior não possuem seção correspondente no BWeb.",
            "Alguns identificadores de urna efetivada se repetem em origem especial no exterior.",
            "Os indicadores são agregados e não identificam votos de pessoas ou a razão de contingências.",
        ]}
    (out_dir/"geografia-2026-2t.json").write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    text=[
        "# FATOVIA AUDITA | Urna, seção e município | 2º turno 2026","",
        f"**Estado:** {state}. **Unidades:** {len(per_uf)}/28. **Seções com BU:** {total:,}. **Códigos municipais por UF:** {len(cities):,}.",
        "", "| UF | Municípios/localidades | Seções BU | CEFT | CEFT sem BU | Urnas substituídas |",
        "|---|---:|---:|---:|---:|---:|"]
    for uf,x in sorted(per_uf.items()):
        text.append(f"| {uf} | {x['municipios']:,} | {x['secoes']:,} | {x['secoes_ceft']:,} | {x['ceft_sem_bu']} | {x['urnas_substituidas']:,} |")
    text+=["","## Arquivos de análise", "",
        "- urnas-secoes-2026-2t.csv.gz: registro por seção com UF, município, zona, seção, urna e totais agregados.",
        "- municipios-2026-2t.csv.gz: indicadores de biometria, comparecimento e dispersão de participação por seção.",
        "- ocorrencias-cidades-2026-2t.csv: ocorrências técnicas históricas associadas às cidades.",
        "","## Limitações",""]
    text.extend("- "+item for item in report["limitacoes"])
    (out_dir/"geografia-2026-2t.md").write_text("\n".join(text)+"\n",encoding="utf-8")
    print(json.dumps({k:report[k] for k in ("status","unidades_geograficas",
        "secoes_bu","municipios_distintos_por_uf","alertas_historicos_georreferenciados_por_nome","falhas")},ensure_ascii=False),flush=True)
    return state=="OK"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="work/geografia")
    p.add_argument("--historico",default="work/geografia-historico")
    p.add_argument("--out",default="work/geografia-consolidado")
    a=p.parse_args()
    if not run(a.input,a.historico,a.out):raise SystemExit(2)

if __name__=="__main__":
    main()
