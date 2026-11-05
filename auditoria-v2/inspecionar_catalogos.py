#!/usr/bin/env python3
"""Consulta estrutura e proveniência dos catálogos públicos TSE (sem dados pessoais)."""
import datetime as dt
import hashlib
import json
import os
import pathlib
import urllib.request
from concurrent.futures import ThreadPoolExecutor

IDS=["comparecimento-e-abstencao-2026","eleitorado-2026",
     "resultados-2026-arquivos-transmitidos-para-totalizacao",
     "resultados-2026","resultados-2026-boletim-de-urna"]
OUT=pathlib.Path(os.getenv("AUDIT_OUT","resultados-catalogos-2026"))
OUT.mkdir(parents=True,exist_ok=True)

def load(slug):
    url="https://dadosabertos.tse.jus.br/api/3/action/package_show?id="+slug
    req=urllib.request.Request(url,headers={"User-Agent":"FatoVia-auditoria-coerencia/2026"})
    with urllib.request.urlopen(req, timeout=90) as response:
        raw=response.read(10*1024*1024)
    data=json.loads(raw)
    if not data.get("success"):
        raise RuntimeError(slug+" não localizado")
    package=data["result"]
    resources=[]
    for x in package.get("resources",[]):
        resources.append({k:x.get(k) for k in (
            "name","description","url","mimetype","format","size","created",
            "last_modified","id","hash","metadata_modified")})
    return {"id":slug,"created":package.get("metadata_created"),
            "modified":package.get("metadata_modified"),"resources":resources}

def main():
    result={"consulted_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
            "sources":{},"errors":[]}
    with ThreadPoolExecutor(max_workers=5) as pool:
        tasks={pool.submit(load,slug):slug for slug in IDS}
        for future,slug in tasks.items():
            try: result["sources"][slug]=future.result()
            except Exception as ex: result["errors"].append({"id":slug,"error":str(ex)})
    path=OUT/"catalogos_2026.json"
    path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    for slug,source in result["sources"].items():
        print(slug, source["modified"], len(source["resources"]))
        for r in source["resources"][:40]:
            print("   ",r["name"],r["size"],r["url"])
    for error in result["errors"]:print("ERRO",error)
    raise SystemExit(0 if not result["errors"] else 2)

if __name__=="__main__":
    main()
