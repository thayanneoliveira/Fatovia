"""Gedai: busca controlada de evidências agregadas para urnas das seções de contingência.

Abre .jez aninhados do portal TSE com hash SHA512 conferido.
Localiza apenas tokens exatos de números de urna (não texto livre nem dados pessoais).
Presença de número em log de PREPARAÇÃO não comprova substituição em seção.
"""
from __future__ import annotations
import argparse,io,zipfile,json,re
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from .gedai_inventario_2026 import discover
from .ma_integral import checked_reference

LIMIT_PER_INNER=30_000_000
LIMIT_TOTAL_TEXT=1_000_000_000
DAY_RE=re.compile(r"(?:20\d{2}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]20\d{2})")
SERIAL_RE=re.compile(r"(?<!\d)0{0,2}(\d{7})(?!\d)")
MARKERS=("carga","prepara","lacra","conting","substit","erro","falha","registro","urna")

def index_targets(csvfile,uf):
    import csv
    out=defaultdict(set)
    secs=defaultdict(set)
    with Path(csvfile).open(encoding="utf-8",newline="") as f:
        for row in csv.DictReader(f):
            for col in ("urna_prevista","urna_efetivada"):
                s=str(row.get(col,"")).strip()
                if s.isascii() and s.isdigit():
                    out[int(s)].add((row["cod_municipio_tse"],row["zona"],row["secao"]))
            secs[(row["cod_municipio_tse"],row["zona"],row["secao"])].add(row.get("municipio",""))
    return out,secs

def analyze_text(data,serials,summary,digest_set):
    try:
        text=data.decode("utf-8-sig",errors="strict")
        enc="utf8"
    except UnicodeError:
        text=data.decode("latin-1",errors="strict")
        enc="latin1"
    summary["encodings"][enc]+=1
    for line in text.splitlines():
        summary["linhas_processadas"]+=1
        matches={int(m.group(1)) for m in SERIAL_RE.finditer(line)}
        matches.intersection_update(serials)
        if not matches:continue
        low=line.casefold()
        for serial in matches:
            record=summary["seriais"][serial]
            record["linhas_com_referencia"]+=1
            for tag in MARKERS:
                if tag in low:record["indicadores"][tag]+=1
            dates=DAY_RE.findall(line)
            for date in dates[:2]:
                if len(record["datas_amostra"])<8:
                    record["datas_amostra"].add(date)

def inspect_zip(z,serials,summary,depth=0):
    if depth>2:
        summary["ignorados_profundidade"]+=1;return
    for item in z.infolist():
        if item.is_dir():continue
        if item.file_size>LIMIT_PER_INNER:
            summary["ignorados_tamanho"]+=1;continue
        if summary["bytes_descompactados_lidos"]+item.file_size>LIMIT_TOTAL_TEXT:
            summary["limite_global_atingido"]=True;return
        name=item.filename.lower()
        if not name.endswith((".jez",".zip",".txt",".dat",".log",".csv")):
            continue
        body=z.read(item)
        summary["bytes_descompactados_lidos"]+=len(body)
        if name.endswith((".jez",".zip")):
            try:
                with zipfile.ZipFile(io.BytesIO(body)) as nested:
                    summary["arquivos_comprimidos_aninhados"]+=1
                    inspect_zip(nested,serials,summary,depth+1)
            except zipfile.BadZipFile:
                summary["arquivos_aninhados_invalidos"]+=1
        else:
            summary["arquivos_textuais"]+=1
            analyze_text(body,serials,summary,None)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--uf",required=True)
    p.add_argument("--csv",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    serials,sections=index_targets(a.csv,a.uf)
    report={"uf":a.uf,"gerado_utc":datetime.now(timezone.utc).isoformat(),
      "status":"INCONCLUSIVO","alvos_urnas_distintas":len(serials),
      "alvos_secoes":len(sections),"dias":{},"notas":[
         "GEDAI registra PREPARAÇÃO de urna, não necessariamente a hora de substituição na votação.",
         "A ausência do número físico de uma urna em logs Gedai não demonstra ausência de preparação.",
         "Tokens numéricos coincidentes precisam de avaliação semântica e confirmação pelo TSE.",
         "Nenhuma linha de log bruto é publicada, apenas contagem e referência de equipamentos.",
      ]}
    try:
        for day in ("24","25"):
            url=discover(a.uf,day)
            with TemporaryDirectory(prefix="fatovia-gedai-pistas-") as d:
                target,meta=checked_reference(url,"gedai.zip",d)
                summary={"fonte":meta,"encodings":Counter(),
                         "arquivos_comprimidos_aninhados":0,
                         "arquivos_aninhados_invalidos":0,
                         "arquivos_textuais":0,
                         "bytes_descompactados_lidos":0,"linhas_processadas":0,
                         "ignorados_profundidade":0,"ignorados_tamanho":0,
                         "limite_global_atingido":False,
                         "seriais":defaultdict(lambda:{"linhas_com_referencia":0,
                                         "indicadores":Counter(),"datas_amostra":set()})}
                with zipfile.ZipFile(target) as z:
                    inspect_zip(z,serials,summary)
                refs={}
                for urn,entry in summary["seriais"].items():
                    refs[str(urn)]={
                      "linhas_com_referencia":entry["linhas_com_referencia"],
                      "indicadores":dict(entry["indicadores"]),
                      "datas_amostra":sorted(entry["datas_amostra"])}
                report["dias"][day]={
                    "fonte":meta,"formatos":{k:dict(v) if isinstance(v,Counter) else v for k,v in summary.items()
                                             if k not in ("seriais","fonte")},
                    "urnas_com_referencia":len(refs),
                    "refs_urnas":refs}
            print(json.dumps({"uf":a.uf,"dia":day,
                "urnas_com_referencia":len(refs),
                "arquivos_internos":summary["arquivos_textuais"],
                "linhas":summary["linhas_processadas"],
                "bytes":summary["bytes_descompactados_lidos"],
                "truncado":summary["limite_global_atingido"]},ensure_ascii=False),flush=True)
        report["status"]="EXTRAIDO_COM_LIMITE" if any(v["formatos"]["limite_global_atingido"] for v in report["dias"].values()) else "EXTRAIDO"
    except Exception as e:
        report["erro"]=f"{type(e).__name__}: {e}"
    target=out/(a.uf+".json")
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"uf":a.uf,"status":report["status"],"erro":report.get("erro"),
                      "urnas_encontradas_por_dia":{k:v["urnas_com_referencia"] for k,v in report["dias"].items()}},ensure_ascii=False),flush=True)
    if report["status"]=="INCONCLUSIVO":raise SystemExit(2)

if __name__=="__main__":main()
