#!/usr/bin/env python3
"""Conferência pública multi-UF: fonte nacional lida UMA vez por lote.

Não trata qualquer divergência como fraude. Não processa dados pessoais.
"""
import argparse
from collections import defaultdict
import csv
import datetime as dt
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import zipfile

SRC=Path(__file__).with_name("auditar_coerencia_2026.py")
spec=importlib.util.spec_from_file_location("fatovia_coerencia",SRC)
a=importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

ALL_UFS=set("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO ZZ".split())
TRIPLET=a.TRIPLET
KEY=a.PRINCIPAL

def detail_many(path,ufs):
    results={uf:{1:{},2:{}} for uf in ufs}
    count=defaultdict(int)
    with zipfile.ZipFile(path) as z:
        members=[n for n in z.namelist() if n.lower().endswith(".csv")]
        if not members:raise RuntimeError("detalhe: ZIP sem CSV")
        brazil=[n for n in members if "BRASIL" in n.upper()]
        if brazil:
            members=brazil
        else:
            # Normalmente um CSV por UF, evita ler o mesmo volume 28 vezes.
            candidates=[n for n in members if any(n.lower().endswith("_"+uf.lower()+".csv") for uf in ufs)]
            if candidates:members=candidates
        for member in members:
            with z.open(member) as f:
                rdr=csv.DictReader(io.TextIOWrapper(f,encoding="latin-1",newline=""),delimiter=";")
                a.require(set(rdr.fieldnames or []),KEY+TRIPLET+("CD_CARGO","NR_TURNO"),member)
                for row in rdr:
                    uf=a.norm(row.get("SG_UF"))
                    if uf not in results or a.norm(row["CD_CARGO"])!="1":continue
                    turno=a.norm(row["NR_TURNO"])
                    if turno not in ("1","2"):continue
                    section=a.key(row)
                    v=tuple(a.get_int(row,col) for col in TRIPLET)
                    store=results[uf][int(turno)]
                    if section in store and store[section]!=v:
                        raise RuntimeError("detalhe: valores inconsistentes na seção: "+str((uf,turno,section)))
                    store[section]=v
                    count[uf]+=1
    return results,count

def elo_many(path,ufs):
    stores={uf:defaultdict(lambda:[0,0,0]) for uf in ufs}
    count=defaultdict(int)
    missing=set(ufs)
    with zipfile.ZipFile(path) as z:
        members=[n for n in z.namelist() if n.lower().endswith(".csv")]
        for uf in ufs:
            target="perfil_comparecimento_abstencao_2026_"+uf+".csv"
            matched=[n for n in members if n.lower().endswith(target.lower())]
            if not matched: continue
            missing.discard(uf)
            for member in matched:
                with z.open(member) as f:
                    reader=csv.DictReader(io.TextIOWrapper(f,encoding="latin-1",newline=""),delimiter=";")
                    a.require(set(reader.fieldnames or []),KEY[:3]+("NR_TURNO","QT_APTOS","QT_COMPARECIMENTO","QT_ABSTENCAO"),member)
                    for row in reader:
                        if a.norm(row["SG_UF"])!=uf:continue
                        t=a.norm(row["NR_TURNO"])
                        if t not in ("1","2"):continue
                        k=(int(t),)+a.key(row,False)
                        vals=[a.get_int(row,col) for col in ("QT_APTOS","QT_COMPARECIMENTO","QT_ABSTENCAO")]
                        for i in range(3):stores[uf][k][i]+=vals[i]
                        count[uf]+=1
    return {uf:{k:tuple(v) for k,v in store.items()} for uf,store in stores.items()},count,sorted(missing)

def compare_uf(uf,bu,detail,elo,perfil):
    """Separar cobertura de segundo turno de seções de primeiro turno/snapshot."""
    counts,rows=a.reconcile(bu,detail,elo,perfil,uf)
    # O comparador base inclui seções APENAS do primeiro turno/perfil como
    # falta de cobertura 2T. Retificamos status mantendo estatísticas brutas
    # auditáveis em campo específico, sem destruir ocorrências.
    changed=0
    for row in rows:
        if row["tipo"]!="AUSENCIA_DE_FONTE_2T":continue
        if row.get("tem_bu") or row.get("tem_detalhe"):continue
        row["tipo"]="FORA_UNIVERSO_DE_VOTACAO_2T"
        row["status"]="SECAO_PRESENTE_APENAS_NO_1T_OU_SNAPSHOT"
        changed+=1
    counts["secoes_exclusivas_1T_ou_perfil_sem_BUs_2T"]=changed
    counts["cobertura_2T_pendente_confirmacao"]=counts.get("BU_ou_detalhe_2T_sem_cobertura",0)-changed
    counts["secoes_2T_somente_bu"]=len(set(bu)-set(detail[2]))
    counts["secoes_2T_somente_detalhe"]=len(set(detail[2])-set(bu))
    counts["secoes_bu_web_2t"]=len(bu)
    counts["secoes_detalhe_1t"]=len(detail[1])
    counts["secoes_detalhe_2t"]=len(detail[2])
    counts["secoes_perfil_eleitorado"]=len(perfil)
    counts["zonas_elo_t1"]=sum(k[0]==1 for k in elo)
    counts["zonas_elo_t2"]=sum(k[0]==2 for k in elo)
    return counts,rows

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ufs",nargs="+",required=True)
    p.add_argument("--data-dir",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args()
    ufs=[x.upper() for x in args.ufs]
    if not ufs or len(ufs)!=len(set(ufs)) or not set(ufs)<=ALL_UFS:
        raise ValueError("lista de unidades inválida")
    args.data_dir.mkdir(parents=True,exist_ok=True)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    summary={"utc":dt.datetime.now(dt.timezone.utc).isoformat(),"units_requested":ufs,
        "units_completed":[],"units_errors":[],"shared_sources":{},
        "limitations":["Dados de óbitos e comparecimento nominal não disponíveis.",
            "Dados de ELO podem conter somente 1T; cobertura e disponibilidade por turno declaradas.",
            "Divergências entre ELO e detalhamento da votação não demonstram fraude; fontes diferem em universo/data.",
            "CSV por cargo sempre filtrado para presidente; 1T não é comparado como se fosse 2T."]}
    downloaded={}
    for kind in ("detalhe","elo"):
        url=a.URLS[kind]
        file=args.data_dir/ url.rsplit("/",1)[-1]
        try:
            a.fetch(url,file)
            downloaded[kind]=file
            summary["shared_sources"][kind]={"url":url,"sha512_local":a.sha512(file),"bytes":file.stat().st_size}
        except Exception as e:
            summary["units_errors"].append({"uf":"ALL","fonte":kind,"erro":str(e)})
    if len(downloaded)==2:
        try:
            details,detail_rows=detail_many(downloaded["detalhe"],ufs)
            elos,elo_rows,elo_missing=elo_many(downloaded["elo"],ufs)
            summary["shared_sources"]["elo"]["ufs_sem_csv"]=elo_missing
            for uf in ufs:
                report={"utc":dt.datetime.now(dt.timezone.utc).isoformat(),"uf":uf,
                        "status":"INCOMPLETE","sources":dict(summary["shared_sources"]),
                        "tests":{},"errors":[]}
                try:
                    url_b=a.URLS["bu"].format(uf=uf)
                    bu_file=args.data_dir/url_b.rsplit("/",1)[-1]
                    a.fetch(url_b,bu_file)
                    a.valid_bu(bu_file,url_b)
                    url_p=a.URLS["perfil"].format(uf=uf)
                    perfil_file=args.data_dir/url_p.rsplit("/",1)[-1]
                    a.fetch(url_p,perfil_file)
                    bu,mb=a.acquire_bu(bu_file,uf)
                    perfil,mp=a.acquire_perfil(perfil_file,uf)
                    if not details[uf][2]:
                        raise RuntimeError("Detalhe eleitoral não possui registros da UF no segundo turno")
                    if not details[uf][1]:
                        raise RuntimeError("Detalhe eleitoral não possui registros da UF no primeiro turno")
                    counts,rows=compare_uf(uf,bu,details[uf],elos[uf],perfil)
                    report["sources"]["bu"]={"url":url_b,"sha512_local":a.sha512(bu_file),
                        "sha512_tse":"MATCH","metrics":mb}
                    report["sources"]["perfil"]={"url":url_p,"sha512_local":a.sha512(perfil_file),
                        "sha512_tse":"NAO_VERIFICADO","metrics":mp}
                    report["sources"]["detalhe_metrics"]={"linhas_filtradas":detail_rows.get(uf,0)}
                    report["sources"]["elo_metrics"]={"linhas_filtradas":elo_rows.get(uf,0),
                                                       "csv_disponivel":uf not in elo_missing}
                    report["tests"]=counts
                    report["limitations"]=summary["limitations"]
                    # Os dados públicos de ELO não são garantidamente disponíveis para 2T;
                    # declarar explicitamente o escopo efetivo.
                    report["status"]="COMPLETE_WITH_ELO_2T" if counts["zonas_elo_t2"] else "COMPLETE_WITHOUT_ELO_2T"
                    with (args.output_dir/(uf+"_excecoes.jsonl")).open("w",encoding="utf-8") as f:
                        for r in rows:f.write(json.dumps(r,ensure_ascii=False)+"\n")
                    summary["units_completed"].append(uf)
                except Exception as e:
                    report["errors"].append(f"{type(e).__name__}: {e}")
                    summary["units_errors"].append({"uf":uf,"erro":str(e)})
                (args.output_dir/(uf+"_manifesto.json")).write_text(
                    json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        except Exception as e:
            summary["units_errors"].append({"uf":"ALL","etapa":"parse_detalhe_ou_elo","erro":str(e)})
    summary["status"]="COMPLETE" if len(summary["units_completed"])==len(ufs) and not summary["units_errors"] else "INCOMPLETE"
    (args.output_dir/"manifesto_lote.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":summary["status"],"completed":summary["units_completed"],
        "errors":summary["units_errors"]},ensure_ascii=False),flush=True)
    sys.exit(0 if summary["status"]=="COMPLETE" else 2)

if __name__=="__main__":
    main()
