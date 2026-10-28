"""Diagnóstico apenas de URLs públicas publicadas pelo TSE, sem baixar arquivos gigantes."""
import json
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError,URLError
from urllib.parse import urlparse
from auditoria.tse import resources

DATASET="resultados-2026-arquivos-transmitidos-para-totalizacao"
OFFICIAL="https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/arqurnatot/"
CANDIDATE=OFFICIAL+"bu_imgbu_logjez_rdv_vscmr_2026_2t_MA.zip"

def metadata(url):
    if urlparse(url).hostname!="cdn.tse.jus.br" or not url.startswith("https://"):
        raise ValueError("Host externo não autorizado")
    req=Request(url,method="HEAD",headers={"User-Agent":"FatoViaAudita/1.0"})
    try:
        with urlopen(req,timeout=30) as r:
            return {"url":url,"status_http":r.status,"bytes":r.headers.get("Content-Length"),
                    "accept_ranges":r.headers.get("Accept-Ranges"),
                    "last_modified":r.headers.get("Last-Modified"),
                    "etag":r.headers.get("ETag")}
    except HTTPError as e:
        return {"url":url,"status_http":e.code,"erro":str(e)}
    except URLError as e:
        return {"url":url,"status":"ERRO_REDE","erro":str(e)}

def main():
    r=resources(DATASET)
    ma=[{"name":x.get("name"),"url":x.get("url")} for x in r
        if x.get("name","").startswith("MA -") or "2t_MA" in x.get("url","")]
    result={"gerado_utc":datetime.now(timezone.utc).isoformat(),
            "recurso_catalogo":ma,"tamanho_catalogo":len(r),
            "candidato_2t":metadata(CANDIDATE)}
    Path("work/aprofundada").mkdir(parents=True,exist_ok=True)
    Path("work/aprofundada/ma_fontes.json").write_text(json.dumps(result,indent=2,ensure_ascii=False))
    print(json.dumps(result,indent=2,ensure_ascii=False))

if __name__=="__main__": main()
