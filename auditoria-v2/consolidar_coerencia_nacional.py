#!/usr/bin/env python3
"""Consolida 4 lotes, validando a cobertura efetiva de 28 unidades e proveniência."""
import argparse
from collections import Counter,defaultdict
import datetime as dt
import json
from pathlib import Path
import sys

UFS=set("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO ZZ".split())
SUM_KEYS=[
 "BU_e_detalhe_2T_ambos","BU_e_detalhe_2T_divergentes",
 "BU_ou_detalhe_2T_sem_cobertura","cobertura_2T_pendente_confirmacao",
 "secoes_exclusivas_1T_ou_perfil_sem_BUs_2T",
 "secoes_bu_web_2t","secoes_detalhe_1t","secoes_detalhe_2t",
 "secoes_2T_somente_bu","secoes_2T_somente_detalhe",
 "secoes_com_dois_turnos","secoes_comparecimento_distinto_entre_turnos",
 "secoes_aptos_distintos_entre_turnos",
 "perfil_e_detalhe_2T_ambos","perfil_aptos_diferentes_2T",
 "zonas_elo_t1","zonas_elo_t2",
 "zonas_ELO_e_detalhe_ambos","zonas_ELO_e_detalhe_diferentes",
 "zonas_sem_cobertura_ambos",
 "secoes_biometria_maior_que_eleitorado_perfil",
 "desbalanceamento_bu","desbalanceamento_detalhe_1t",
 "desbalanceamento_detalhe_2t","excecoes_documentais",
]
def run(root,out):
    status={"created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "status":"INCOMPLETE","reconciliation":"BU web + detalhe 1T/2T + perfil pré-voto + ELO por zona",
      "uf_results":{},"summary":{},"errors":[],"limitations":[
       "Sem vínculo individual CPF/título→comparecimento, não verifica alegação de falecidos.",
       "Todas as fontes públicas provêm do TSE, embora de subsistemas diferentes.",
       "ELO não disponibilizado no segundo turno para certas UFs é lacuna de cobertura.",
       "Comparações entre turnos e perfil pré-eleição indicam alterações, não fraudes.",
      ]}
    seen=set(); lots=list(root.rglob("manifesto_lote.json"))
    if len(lots)!=4:status["errors"].append("esperados 4 lotes, encontrados "+str(len(lots)))
    source_hashes=defaultdict(set)
    for p in lots:
        lot=json.loads(p.read_text(encoding="utf-8"))
        if lot.get("status")!="COMPLETE":
            status["errors"].append("lote não concluído: "+str(p)+": "+repr(lot.get("units_errors")))
        for source,v in lot.get("shared_sources",{}).items():
            source_hashes[source].add(v.get("sha512_local",""))
        for uf in lot.get("units_requested",[]):
            if uf not in UFS:status["errors"].append("UF desconhecida: "+uf)
            if uf in seen:status["errors"].append("UF duplicada: "+uf)
            seen.add(uf)
            f=p.with_name(uf+"_manifesto.json")
            if not f.exists():
                status["errors"].append("manifesto de UF ausente: "+str(f))
                continue
            item=json.loads(f.read_text(encoding="utf-8"))
            if item.get("status") not in ("COMPLETE_WITH_ELO_2T","COMPLETE_WITHOUT_ELO_2T"):
                status["errors"].append("UF não processada: "+uf+": "+repr(item.get("errors")))
                continue
            numbers=item.get("tests",{})
            stats={k:int(numbers.get(k,0)) for k in SUM_KEYS}
            stats["elo_2t_disponivel"]=item["status"]=="COMPLETE_WITH_ELO_2T"
            stats["status"]=item["status"]
            stats["source_sha512"]={x:item["sources"].get(x,{}).get("sha512_local") for x in ("bu","perfil")}
            status["uf_results"][uf]=stats
    if seen!=UFS:status["errors"].append("universo incompleto: "+str(sorted(UFS-seen)))
    if set(status["uf_results"])!=UFS:status["errors"].append("UFs concluídas incompletas: "+str(sorted(UFS-set(status["uf_results"]))))
    for source,hashes in source_hashes.items():
        if len(hashes)!=1:
            status["errors"].append("fonte nacional mudou entre lotes: "+source+": "+repr(hashes))
    status["shared_source_sha512"]={source:next(iter(hashes)) for source,hashes in source_hashes.items() if hashes}
    totals=Counter()
    for row in status["uf_results"].values():
        totals.update({k:row[k] for k in SUM_KEYS})
    status["summary"]=dict(totals)
    status["ufs_com_ELO_2T"]=[uf for uf,v in sorted(status["uf_results"].items()) if v["elo_2t_disponivel"]]
    if not status["errors"]:
        if totals["secoes_bu_web_2t"]!=499207:
            status["errors"].append("seções BU diferentes das 499207 esperadas; revisar versões do universo")
        if totals["secoes_bu_web_2t"] != totals["BU_e_detalhe_2T_ambos"]+totals["secoes_2T_somente_bu"]:
            status["errors"].append("denominador BU não reconciliável com interseção e ausências")
        if totals["secoes_detalhe_2t"] != totals["BU_e_detalhe_2T_ambos"]+totals["secoes_2T_somente_detalhe"]:
            status["errors"].append("denominador detalhe não reconciliável com interseção e ausências")
        if totals["BU_e_detalhe_2T_divergentes"]<0:
            status["errors"].append("contagem inválida")
    status["status"]="COMPLETE_PUBLIC_CONSISTENCY_CHECK" if not status["errors"] else "INCOMPLETE"
    out.mkdir(parents=True,exist_ok=True)
    (out/"resumo_nacional_coerencia_2026.json").write_text(
        json.dumps(status,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":status["status"],"ufs_validas":len(status["uf_results"]),
        "summary":status["summary"],"errors":status["errors"]},ensure_ascii=False),flush=True)
    return 0 if status["status"]=="COMPLETE_PUBLIC_CONSISTENCY_CHECK" else 2

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input-dir",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    opts=p.parse_args()
    sys.exit(run(opts.input_dir,opts.output_dir))
