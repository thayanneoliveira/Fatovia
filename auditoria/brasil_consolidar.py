"""Consolida somente relatórios realmente produzidos nas 28 UFs."""
from pathlib import Path
import json
from datetime import datetime,timezone
from .tse import UFS

VALID={
    "ALERTAS_TECNICOS_REQUEREM_ANALISE",
    "CONFERENCIA_INTERNA_CONSISTENTE_COM_RESSALVAS",
}

def merge(input_dir,out_dir):
    input_dir=Path(input_dir)
    out_dir=Path(out_dir)
    out_dir.mkdir(parents=True,exist_ok=True)
    results={}
    all_alerts={}
    total_sections=0
    total_bu_matches=0
    total_sha_matches=0
    errors=0
    for uf in UFS:
        p=input_dir/(uf+".json")
        if not p.is_file():
            results[uf]={"uf":uf,"status":"NAO_EXECUTADO","erro":"Sem artefato disponível"}
            continue
        try:
            d=json.loads(p.read_text(encoding="utf-8"))
            if d.get("uf")!=uf:
                raise ValueError("UF do artefato não confere")
            coverage=d.get("cobertura",{})
            ver=d.get("verificacoes",{})
            r={
                "uf":uf,"status":d.get("status","INCONCLUSIVO"),
                "secoes_referencia_bu":coverage.get("secoes_bu"),
                "secoes_processadas":coverage.get("secoes_processadas"),
                "secoes_alertadas":coverage.get("secoes_alertadas"),
                "rdv_bu_coincidentes":ver.get("rdv_contagens_confere_bu_ok",0),
                "sha512_arquivos_coincidentes":ver.get("sha512_arquivos_ok",0),
                "ocorrencias":d.get("ocorrencias",{}),
            }
            if d.get("erro"):
                r["erro"]=d["erro"]
            results[uf]=r
            if r["status"] in VALID:
                total_sections+=r["secoes_processadas"] or 0
                total_bu_matches+=r["rdv_bu_coincidentes"]
                total_sha_matches+=r["sha512_arquivos_coincidentes"]
            for typ,n in r["ocorrencias"].items():
                all_alerts[typ]=all_alerts.get(typ,0)+n
        except Exception as exc:
            errors+=1
            results[uf]={"uf":uf,"status":"INCONCLUSIVO",
                         "erro":f"Falha ao ler artefato: {type(exc).__name__}: {exc}"}
    completed=sum(r["status"] in VALID for r in results.values())
    inconclusive=[uf for uf,r in results.items() if r["status"] not in VALID]
    aggregate={
        "projeto":"FATOVIA AUDITA","ano":2026,"turno":2,
        "gerado_utc":datetime.now(timezone.utc).isoformat(),
        "status":"CONCLUIDO_COM_RESSALVAS" if completed==len(UFS) else "PARCIAL",
        "ufs_esperadas":len(UFS),"ufs_com_auditoria_executada":completed,
        "ufs_pendentes":inconclusive,
        "secoes_processadas_em_ufs_concluidas":total_sections,
        "secoes_rdv_igual_bu_em_ufs_concluidas":total_bu_matches,
        "sha512_de_arquivos_conferidos_em_ufs_concluidas":total_sha_matches,
        "ocorrencias_agregadas":all_alerts,
        "por_uf":results,
        "ressalvas":[
            "A validação integral de assinatura criptográfica e certificado NÃO foi realizada.",
            "Os arquivos de urna aqui analisados são somente os publicados como Totalizado.",
            "Correspondência de RDV e BU não demonstra necessariamente intenção do eleitor.",
            "UF sem artefato validado NÃO pode ser contada como auditada.",
        ],
    }
    (out_dir/"brasil-2026-2t.json").write_text(json.dumps(aggregate,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=[
        "# FATOVIA AUDITA | Brasil | 2º turno presidencial 2026",
        "",
        "**Cobertura: "+str(completed)+"/"+str(len(UFS))+" UFs com relatórios tecnicamente executados.**",
        "",
        "**Estado da coleta:** "+aggregate["status"]+".",
        "",
        "| UF | Situação | Seções | RDV=BU | Alertas |",
        "|---|---|---:|---:|---:|",
    ]
    for uf in UFS:
        r=results[uf]
        lines.append("| "+uf+" | "+r["status"]+" | "+str(r.get("secoes_processadas","-"))+" | "+
            str(r.get("rdv_bu_coincidentes","-"))+" | "+str(r.get("secoes_alertadas","-"))+" |")
    lines.extend([
        "","## Limitações",
        "",*["- "+s for s in aggregate["ressalvas"]],
        "",
        "## Metodologia e dados",
        "",
        "- Dados do TSE: BU por UF, CEFT por UF e arquivos brutos totalizados.",
        "- Cada UF é auditada e contabilizada separadamente.",
        "- A ausência de conclusão de uma UF não invalida outras, mas impede afirmar auditoria integral do Brasil.",
        "- Resultados detalhados: arquivos JSON no diretório docs/auditoria/brasil-2026-2t/ufs.",
        "",
    ])
    (out_dir/"brasil-2026-2t.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({"status":aggregate["status"],"ufs":completed,
                      "secoes":total_sections,"pendentes":inconclusive},ensure_ascii=False),flush=True)
    return aggregate

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="work/brasil")
    p.add_argument("--output",default="work/brasil-consolidado")
    a=p.parse_args()
    merge(a.input,a.output)
