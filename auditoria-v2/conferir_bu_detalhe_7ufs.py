#!/usr/bin/env python3
"""Conferência complementar de BU × detalhe da apuração presidencial (2T), UF por UF."""
import argparse
import datetime as dt
import importlib.util
import json
from pathlib import Path
import sys

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(path))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

a=load("fatovia_coerencia","auditar_coerencia_2026.py")
batch=load("fatovia_batch","auditar_coerencia_lote.py")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ufs",nargs="+",required=True)
    p.add_argument("--data-dir",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args()
    ufs=[x.upper() for x in args.ufs]
    args.data_dir.mkdir(parents=True,exist_ok=True)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    out={"utc":dt.datetime.now(dt.timezone.utc).isoformat(),
         "scope":"2T PRESIDENTE; BU WEB x DETALHE VOTACAO SECAO, apenas quantitativos",
         "ufs_requested":ufs,"status":"INCOMPLETE","results":{},"errors":[],
         "limitation":"Não inclui perfil, ELO, RDV, logs ou dados nominais. Não verifica votos atribuídos a falecidos."}
    try:
        detail_url=a.URLS["detalhe"]
        detail_path=args.data_dir/detail_url.rsplit("/",1)[-1]
        a.fetch(detail_url,detail_path)
        out["detail_sha512_local"]=a.sha512(detail_path)
        d,counts=batch.detail_many(detail_path,ufs)
        total=0
        for uf in ufs:
            try:
                url=a.URLS["bu"].format(uf=uf)
                path=args.data_dir/url.rsplit("/",1)[-1]
                a.fetch(url,path)
                a.valid_bu(path,url)
                b,meta=a.acquire_bu(path,uf)
                det=d[uf][2]
                both=set(b)&set(det)
                mismatches=[k for k in both if b[k]!=det[k]]
                only_bu=sorted(set(b)-set(det))
                only_det=sorted(set(det)-set(b))
                checks=sum(1 for v in b.values() if v[0]!=v[1]+v[2])
                result={"uf":uf,"secoes_bu":len(b),"secoes_detalhe":len(det),
                    "secoes_cruzadas":len(both),"diferencas_comparecimento":len(mismatches),
                    "secoes_somente_bu":len(only_bu),"secoes_somente_detalhe":len(only_det),
                    "incoerencias_aptos_comparecimento_abstencao":checks,
                    "bu_sha512":a.sha512(path),"bu_sha_tse":"MATCH",
                    "status":"COMPLETE",
                    "exemplos_divergencia":[{"secao":list(k),"bu":b[k],"detalhe":det[k]} for k in mismatches[:50]],
                    "exemplos_ausencia_bu":[list(k) for k in only_det[:50]],
                    "exemplos_ausencia_detalhe":[list(k) for k in only_bu[:50]]}
                out["results"][uf]=result
                print("VERIFICADO",uf,len(both),"dif",len(mismatches),"so_bu",len(only_bu),"so_det",len(only_det),flush=True)
            except Exception as e:
                out["errors"].append({"uf":uf,"erro":str(e)})
        if len(out["results"])==len(ufs) and not out["errors"]:
            out["status"]="COMPLETE_QUANTITATIVOS_2T"
    except Exception as e:
        out["errors"].append({"uf":"ALL","erro":str(e)})
    (args.output_dir/"conferencia_bu_detalhe_t2.json").write_text(
        json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("RESULTADO",out["status"],out["errors"],flush=True)
    sys.exit(0 if out["status"].startswith("COMPLETE") else 2)

if __name__=="__main__":main()
