"""Diagnóstico PASSIVO de 3 conjuntos publicados pelo TSE, segundo turno 2026.

Somente GET dos URLs publicados oficialmente, sem descoberta de rotas,
acesso autenticado, exploração de vulnerabilidade ou processamento de dados pessoais.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import tempfile
import zipfile

from .tse import download_zip, sha512_expected

BASE="https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/"
FILES={
    "esperada_24": BASE+"correspesp/CESP_2t_MA_241020261231.zip",
    "esperada_25": BASE+"correspesp/CESP_2t_MA_251020261345.zip",
    "efetivada_26": BASE+"correspefet/CEFT_2t_MA_261020261201.zip",
}

def inspect(name, path):
    contents=[]
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            obj={"arquivo":info.filename,"bytes":info.file_size}
            if info.filename.lower().endswith(".csv"):
                with z.open(info) as raw:
                    with io.TextIOWrapper(raw,encoding="latin-1",newline="") as stream:
                        rdr=csv.reader(stream,delimiter=";")
                        head=next(rdr,None)
                        obj["colunas"]=head
                        obj["linhas"]=sum(1 for _ in rdr)
            contents.append(obj)
    return contents

def main():
    result={"fase":"diagnostico_estrutura","uf":"MA","turno":2,
            "gerado_utc":datetime.now(timezone.utc).isoformat(),
            "observacao":"Fonte publicada no TSE; não se busca acesso a sistemas internos.",
            "arquivos":{}, "status":"OK"}
    with tempfile.TemporaryDirectory() as tmp:
        for name,url in FILES.items():
            item={"url":url,"hash_url":url+".sha512"}
            try:
                path=Path(tmp)/(name+".zip")
                expected=sha512_expected(item["hash_url"])
                actual,size=download_zip(url,path)
                item.update({"hash_sha512_publicado":expected,
                             "hash_sha512_calculado":actual,
                             "hash_conferido":actual==expected,
                             "bytes_zip":size})
                if not item["hash_conferido"]:
                    raise ValueError("SHA512 difere do publicado")
                item["conteudo"]=inspect(name,path)
            except Exception as exc:
                item["erro"]=str(exc)
                result["status"]="INCONCLUSIVO"
            result["arquivos"][name]=item
    Path("work/proveniencia").mkdir(parents=True,exist_ok=True)
    out="work/proveniencia/ma_estrutura.json"
    Path(out).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"detalhes":[
        {"arquivo":k,"hash_ok":v.get("hash_conferido"),
         "estrutura":v.get("conteudo"),"erro":v.get("erro")}
        for k,v in result["arquivos"].items()]},indent=2,ensure_ascii=False))
    if result["status"]!="OK":
        raise SystemExit(1)

if __name__=="__main__":
    main()
