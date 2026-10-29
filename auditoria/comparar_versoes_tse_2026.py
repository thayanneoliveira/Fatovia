"""Audita se arquivos TSE 2026 2T mudaram desde snapshots gravados em 28/10.

Comparação forte: SHA512 calculado dos bytes ATUAIS x SHA512 do snapshot.
Comparação fraca: apenas tamanho/HEAD; não prova que conteúdo é igual.
TSE pode publicar revisões; alteração NÃO demonstra investigação ou fraude.
Fontes e downloads somente em cdn.tse.jus.br; nenhuma interface privada.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
from urllib.request import Request,urlopen
import zipfile

from .tse import download_zip,sha512_expected
from .ma_integral import stream_full_zip

HOST="cdn.tse.jus.br"
OUTCOME={"INALTERADO","ALTERADO","INCONCLUSIVO"}

def permitted(url):
    p=urlparse(url)
    if p.scheme!="https" or p.hostname!=HOST or not p.path.startswith("/estatistica/sead/eleicoes/eleicoes2026/"):
        raise ValueError("URL fora das fontes permitidas do TSE")
    return url

def head(url):
    with urlopen(Request(permitted(url),method="HEAD",
        headers={"User-Agent":"FatoViaAudita/2026 (verificacao-de-versoes)"}),timeout=80) as resp:
        if resp.status!=200:raise ValueError("HEAD HTTP "+str(resp.status))
        length=resp.headers.get("Content-Length")
        if not length or int(length)<=0:raise ValueError("Sem tamanho HTTP confiável")
        return {
            "content_length":int(length),
            "etag":resp.headers.get("ETag"),
            "last_modified":resp.headers.get("Last-Modified"),
            "http_status":resp.status,
        }

def check_zip(kind,old,temp):
    url=permitted(old["url"])
    result={"tipo":kind,"url":url,"hash_anterior":old.get("sha512"),
            "bytes_anteriores":old.get("bytes"),
            "hash_atual":None,"hash_declarado_tse_atual":None,
            "status":"INCONCLUSIVO"}
    try:
        result["head"]=head(url)
        ref=sha512_expected(url+".sha512")
        result["hash_declarado_tse_atual"]=ref
        digest,size=download_zip(url,Path(temp)/(kind+".zip"))
        result["hash_atual"]=digest
        result["bytes_atuais"]=size
        result["zip_valido"]=zipfile.is_zipfile(Path(temp)/(kind+".zip"))
        result["hash_confere_manifesto_atual"]=digest==ref
        if not result["zip_valido"] or not result["hash_confere_manifesto_atual"]:
            result["status"]="INCONCLUSIVO"
            result["erro"]="O ZIP atual não foi validado pelo SHA512 oficial ou formato"
        elif not old.get("sha512"):
            result["status"]="INCONCLUSIVO"
            result["erro"]="Sem hash histórico capturado"
        elif digest==old["sha512"]:
            result["status"]="INALTERADO"
        else:
            result["status"]="ALTERADO"
            result["nota"]="Conteúdo mudou desde snapshot; motivo da alteração é desconhecido"
    except Exception as exc:
        result["erro"]=f"{type(exc).__name__}: {exc}"
    return result

def check_raw(old,temp,limit):
    url=permitted(old["url"])
    previous=old.get("sha512_calculado")
    prevbytes=old.get("bytes",old.get("bytes_remotos"))
    result={"tipo":"arquivos_transmitidos_totalizados",
            "url":url,"hash_anterior":previous,
            "bytes_anteriores":prevbytes,"status":"INCONCLUSIVO"}
    try:
        h=head(url)
        result["head"]=h
        result["tamanho_atual_igual_ao_anterior"]=h["content_length"]==prevbytes
        if h["content_length"] != prevbytes:
            result["status"]="ALTERACAO_DE_TAMANHO"
            result["nota"]="Tamanho diferente; não concluir conteúdo/cause sem download"
        if previous and h["content_length"]<=limit and h["content_length"]<=5_000_000_000:
            details=stream_full_zip(url,Path(temp)/"raw.zip")
            result["hash_atual"]=details["sha512_calculado"]
            result["status"]="INALTERADO" if result["hash_atual"]==previous else "ALTERADO"
            result["metodo"]="SHA512 completo dos bytes"
        else:
            result["metodo"]="Somente HEAD (tamanho, ETag e Last-Modified)"
            result["nota"]="Sem comparação criptográfica dos bytes atuais. Tamanho igual NÃO prova mesmo conteúdo."
    except Exception as exc:
        result["erro"]=f"{type(exc).__name__}: {exc}"
    return result

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--uf",required=True)
    a.add_argument("--original",required=True)
    a.add_argument("--bu-historico",required=True)
    a.add_argument("--out",required=True)
    a.add_argument("--raw-max",type=int,default=0)
    x=a.parse_args()
    original=json.loads(Path(x.original).read_text(encoding="utf-8"))
    old_bu=json.loads(Path(x.bu_historico).read_text(encoding="utf-8"))
    if original.get("uf")!=x.uf or original.get("ano")!=2026 or original.get("turno")!=2:
        raise ValueError("Baseline não corresponde à UF/eleição esperada")
    older=old_bu["arquivos_por_uf"][x.uf]
    if older["sha512_calculado"]!=original["fontes"]["bu"]["sha512"]:
        raise ValueError("Referências históricas BU de 28/10 discordam")
    report={"uf":x.uf,"data_consulta_utc":datetime.now(timezone.utc).isoformat(),
       "baseline_BU_utc":older.get("gerado_em_utc"),
       "baseline_pacote_utc":original.get("data_utc"),
       "referencia":"Snapshots FatoVia de 28/10/2026, NÃO necessariamente a publicação inicial do TSE",
       "resultados":{},"ressalvas":[
           "Identidade de hash de arquivo não atesta integridade do processo eleitoral inteiro.",
           "Diferença de hash isolada não implica investigação, fraude ou manipulação.",
           "Data Last-Modified/ETag fornecidos por CDN não substituem verificação dos bytes.",
           "Para arquivos brutos superiores ao limite, não existe conclusão de conteúdo inalterado.",
       ]}
    with TemporaryDirectory(prefix=f"fatovia-versoes-{x.uf}-") as tmp:
        for kind in ("bu","ceft"):
            report["resultados"][kind]=check_zip(kind,original["fontes"][kind],tmp)
            print(f"{x.uf} {kind}: {report['resultados'][kind]['status']}",flush=True)
        report["resultados"]["bruto"]=check_raw(
            original["fontes"]["arquivo_bruto"],tmp,x.raw_max)
        print(f"{x.uf} bruto: {report['resultados']['bruto']['status']}",flush=True)
    out=Path(x.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"uf":x.uf, "estados":{k:v["status"] for k,v in report["resultados"].items()}},ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
