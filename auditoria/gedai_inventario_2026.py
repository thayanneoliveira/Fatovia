"""Inventário verificável dos logs públicos Gedai no segundo turno de 2026.

Objetivo: reconhecer formato e cobertura dos logs de PREPARAÇÃO; ainda NÃO
equiparar um evento Gedai a troca de equipamento no dia de votação.
Sem imprimir linhas brutas ou informações pessoais de logs.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
import json, re, zipfile, hashlib
from .tse import UFS,fetch
from .ma_integral import checked_reference

CATALOG="https://dadosabertos.tse.jus.br/dataset/resultados-2026-logs-do-sistema-de-preparacao-das-urnas-eletronicas-gedai-2-turno"
ROOT="https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/logsgedai/"
MAX_FILE=150_000_000
MAX_UNCOMPRESSED=550_000_000

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values=set()
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            u=dict(attrs).get("href","")
            if u.startswith(ROOT):
                self.values.add(u)

def discover(uf,day):
    if uf not in UFS or day not in ("24","25"):
        raise ValueError("UF ou dia inválido")
    obj=Links()
    obj.feed(fetch(CATALOG,max_bytes=4_000_000).decode("utf-8"))
    pattern=rf"{re.escape(ROOT)}log_gedai_2t_{uf}_{day}102026\d{{4}}\.zip"
    urls=sorted(u for u in obj.values if re.fullmatch(pattern,u))
    if len(urls)!=1:
        raise ValueError(f"Catálogo com {len(urls)} arquivos para {uf}/{day}, esperado um; não adivinhar URL.")
    url=urls[0]
    if url+".sha512" not in obj.values:
        raise ValueError("Hash oficial não listado para ZIP")
    return url

def summary(uf,day,outdir):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    report={"uf":uf,"dia":"2026-10-"+day,"gerado_utc":datetime.now(timezone.utc).isoformat(),
        "status":"INCONCLUSIVO","fonte":{},"zip":{},"formato":{},"limites":[
            "Inventário de Gedai identifica preparação de urnas; não prova troca em determinado horário.",
            "Leitura de textos é contada por características gerais, sem publicar linhas de log ou dados pessoais.",
            "A ausência de chave numa amostra não significa ausência no arquivo completo.",
        ]}
    try:
        url=discover(uf,day)
        with TemporaryDirectory(prefix="fatovia-gedai-") as td:
            zip_path,meta=checked_reference(url,"gedai.zip",td)
            report["fonte"]=meta
            types=Counter()
            files=0
            total_bytes=0
            maxfiles=[]
            size_skipped=0
            for zinfo in zipfile.ZipFile(zip_path).infolist():
                if zinfo.is_dir():continue
                files+=1
                suffix=Path(zinfo.filename).suffix.lower()
                types[suffix or "<sem_extensao>"]+=1
                total_bytes+=zinfo.file_size
                if len(maxfiles)<15:
                    maxfiles.append({"sufixo":suffix or "<sem_extensao>","bytes":zinfo.file_size,
                                     "nome_sha256":hashlib.sha256(zinfo.filename.encode()).hexdigest()[:16]})
                if zinfo.file_size>MAX_FILE:size_skipped+=1
            report["zip"]={"entradas":files,"bytes_descomprimidos_declarados":total_bytes,
                           "tipos":dict(types),"arquivos_acima_limite_individual":size_skipped,
                           "amostra_anonima":maxfiles}
            report["status"]="INVENTARIO_CONCLUIDO"
            if total_bytes>MAX_UNCOMPRESSED:
                report["formato"]["leitura_textual"]="NAO_REALIZADA_LIMITE"
            else:
                counters=Counter()
                encodings=Counter()
                examples={}
                with zipfile.ZipFile(zip_path) as zf:
                    for zinfo in zf.infolist():
                        if zinfo.is_dir() or zinfo.file_size>MAX_FILE:continue
                        if not zinfo.filename.lower().endswith((".txt",".log",".csv",".dat")):
                            continue
                        data=zf.read(zinfo)
                        enc=None
                        for encoding in ("utf-8-sig","latin-1"):
                            try:
                                text=data.decode(encoding,errors="strict")
                                enc=encoding
                                break
                            except UnicodeError:pass
                        if not enc:
                            counters["textos_nao_decodificaveis"]+=1
                            continue
                        encodings[enc]+=1
                        lines=text.splitlines()
                        counters["linhas"]+=len(lines)
                        counters["linhas_com_urna"]+=sum("urna" in s.lower() for s in lines)
                        counters["linhas_com_carga"]+=sum("carga" in s.lower() for s in lines)
                        counters["linhas_com_contingencia"]+=sum("conting" in s.lower() for s in lines)
                        counters["linhas_com_erro"]+=sum("erro" in s.lower() or "falha" in s.lower() for s in lines)
                        counters["linhas_com_data"]+=sum(bool(re.search(r"\d{2}/\d{2}/20\d\d|20\d\d-\d\d-\d\d",s)) for s in lines)
                        for line in lines[:8]:
                            fields=line.split("\t")
                            key=f"num_campos_tab_{min(len(fields),12)}"
                            counters[key]+=1
                report["formato"]={"indicadores":dict(counters),"encodings":dict(encodings),
                                   "leitura_textual":"AMOSTRA_ESTRUTURAL_SEM_PUBLICAR_DADOS"}
    except Exception as e:
        report["erro"]=f"{type(e).__name__}: {e}"
    target=outdir/(f"{uf}-{day}.json")
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"uf":uf,"dia":day,"status":report["status"],
        "fonte":report.get("fonte",{}).get("url"),"zip":report["zip"],
        "formato":report["formato"],"erro":report.get("erro")},ensure_ascii=False),flush=True)
    return report["status"]=="INVENTARIO_CONCLUIDO"

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--uf",required=True,choices=UFS)
    p.add_argument("--dia",required=True,choices=("24","25"))
    p.add_argument("--out",default="work/gedai-inventario")
    a=p.parse_args()
    if not summary(a.uf,a.dia,a.out):
        raise SystemExit(2)
