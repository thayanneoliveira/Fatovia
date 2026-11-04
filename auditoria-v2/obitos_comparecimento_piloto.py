#!/usr/bin/env python3
"""Piloto público de consistência de comparecimento por seção (2026, segundo turno).

Confronta dois produtos públicos do TSE:
- BU WEB da UF (quantitativos por seção, repetidos em linhas de votáveis)
- Detalhe da apuração por seção (quantitativos por seção e cargo)
NÃO contém CPFs, títulos, nomes ou óbitos; não verifica 'voto de falecido'.
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT_BU = "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/buweb/"
ROOT_DETAIL = "https://cdn.tse.jus.br/estatistica/sead/odsele/detalhe_votacao_secao/"
COLUMNS = ("QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES")
KEY = ("SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO")

def canon(s):
    s = (s or "").strip()
    return str(int(s)) if s.isdecimal() else s.upper()

def sha512(file):
    h = hashlib.sha512()
    with file.open("rb") as stream:
        for b in iter(lambda: stream.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()

def download(url, target, limit=1300*1024*1024):
    if target.exists() and target.stat().st_size:
        return
    temp = Path(str(target) + ".part")
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"FatoVia-auditoria-publica/2026"})
        with urllib.request.urlopen(req, timeout=150) as r, temp.open("wb") as f:
            size = 0
            for block in iter(lambda: r.read(1024*1024), b""):
                size += len(block)
                if size > limit:
                    raise RuntimeError("download excede limite da auditoria")
                f.write(block)
        temp.replace(target)
    finally:
        if temp.exists():
            temp.unlink()

def require_bu_checksum(zip_path):
    checksum = Path(str(zip_path) + ".sha512")
    download(ROOT_BU + checksum.name, checksum, limit=1024*1024)
    raw = checksum.read_text(encoding="utf-8-sig", errors="replace")
    import re
    values = {v.lower() for v in re.findall(r"\b[a-fA-F0-9]{128}\b", raw)}
    if len(values) != 1 or next(iter(values)) != sha512(zip_path):
        raise ValueError("SHA-512 do BU web não confere com o publicado")

def entries(zip_path, uf, kind):
    out, read_rows, useful_files, conflicts = {}, 0, [], []
    with zipfile.ZipFile(zip_path) as archive:
        members = [x for x in archive.namelist() if x.lower().endswith(".csv")]
        if not members:
            raise ValueError(f"{kind}: ZIP sem CSV")
        # Prefere arquivo consolidado BRASIL quando o ZIP apresenta ambos os tipos.
        if kind == "detail" and any("BRASIL" in x.upper() for x in members):
            members = [x for x in members if "BRASIL" in x.upper()]
        for member in members:
            with archive.open(member) as raw:
                txt = io.TextIOWrapper(raw, encoding="latin-1", newline="")
                header = txt.readline()
                if not header:
                    continue
                delim = ";" if header.count(";") >= header.count(",") else ","
                fieldnames = next(csv.reader([header], delimiter=delim))
                missing = set(KEY + COLUMNS + ("NR_TURNO",)) - set(fieldnames)
                if missing:
                    raise ValueError(f"{kind}: colunas ausentes em {member}: {sorted(missing)}")
                if kind == "detail" and not ("CD_CARGO" in fieldnames or "DS_CARGO" in fieldnames):
                    raise ValueError("detalhe sem código ou descrição de cargo")
                useful_files.append(member)
                for row in csv.DictReader(txt, fieldnames=fieldnames, delimiter=delim):
                    if canon(row.get("SG_UF")) != uf or canon(row["NR_TURNO"]) != "2":
                        continue
                    if kind == "detail":
                        cargo = canon(row.get("CD_CARGO"))
                        if cargo != "1" and canon(row.get("DS_CARGO")) not in ("PRESIDENTE", "PRESIDENTE DA REPÚBLICA"):
                            continue
                    key = tuple(canon(row.get(k)) for k in KEY)
                    if not all(key):
                        raise ValueError(f"{kind}: chave de seção vazia em {member}")
                    v = tuple(int((row.get(k) or "").strip()) for k in COLUMNS)
                    if min(v) < 0:
                        raise ValueError(f"{kind}: quantitativo negativo em {key}")
                    if key in out and out[key] != v:
                        conflicts.append({"secao":list(key),"valores_anteriores":out[key],"valores_novos":v,"arquivo":member})
                    else:
                        out[key] = v
                    read_rows += 1
    if not out or conflicts:
        raise ValueError(f"{kind}: {len(out)} seções, {len(conflicts)} conflitos: {conflicts[:2]}")
    return out, {"arquivos_csv":useful_files,"linhas_filtradas":read_rows,"secoes":len(out)}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--uf", default="AC")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    uf = a.uf.upper()
    if len(uf) != 2 or not uf.isalpha():
        raise ValueError("UF inválida")
    a.out.mkdir(parents=True, exist_ok=True)
    cache = a.out / "cache"
    cache.mkdir(exist_ok=True)
    bu = cache / f"bweb_2t_{uf}_261020260742.zip"
    detail = cache / "detalhe_votacao_secao_2026.zip"
    download(ROOT_BU + bu.name, bu)
    require_bu_checksum(bu)
    download(ROOT_DETAIL + detail.name, detail)
    b, bm = entries(bu, uf, "bu")
    d, dm = entries(detail, uf, "detail")
    differences = []
    sums = {"bu": [0,0,0], "detalhe": [0,0,0]}
    conserv = {"bu":0,"detalhe":0}
    for base, label in [(b,"bu"),(d,"detalhe")]:
        for v in base.values():
            for i in range(3):
                sums[label][i] += v[i]
            if v[0] != v[1] + v[2]:
                conserv[label] += 1
    for key in sorted(set(b) | set(d)):
        x, y = b.get(key), d.get(key)
        if x == y:
            continue
        kind = "ausente_bu" if x is None else "ausente_detalhe" if y is None else "divergencia_quantitativa"
        differences.append({"uf":key[0],"municipio":key[1],"zona":key[2],"secao":key[3],
                            "tipo":kind,"aptos_bu":x[0] if x else "",
                            "comparecimento_bu":x[1] if x else "", "abstencoes_bu":x[2] if x else "",
                            "aptos_detalhe":y[0] if y else "",
                            "comparecimento_detalhe":y[1] if y else "",
                            "abstencoes_detalhe":y[2] if y else ""})
    cols=["uf","municipio","zona","secao","tipo","aptos_bu","comparecimento_bu",
          "abstencoes_bu","aptos_detalhe","comparecimento_detalhe","abstencoes_detalhe"]
    with (a.out / "excecoes_comparecimento_por_secao.csv").open("w",encoding="utf-8",newline="") as f:
        wr=csv.DictWriter(f,fieldnames=cols);wr.writeheader();wr.writerows(differences)
    result={
        "consulta_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "uf":uf,"turno":2,"status":"COMPARACAO_PUBLICA_CONCLUIDA",
        "sem_dados_pessoais":True,
        "limitacao":"Consistência quantitativa por seção. Não identifica eleitores nem comprova votos de falecidos.",
        "origens":{
            "bu":{"url":ROOT_BU+bu.name,"sha512_zip":sha512(bu),"checksum_tse":"MATCH",**bm},
            "detalhe":{"url":ROOT_DETAIL+detail.name,"sha512_zip":sha512(detail),
                       "checksum_tse":"NAO_CONFERIDO; SHA apenas da copia adquirida",**dm}},
        "secoes_em_ambas":len(set(b)&set(d)),
        "secoes_exclusivas_bu":len(set(b)-set(d)),
        "secoes_exclusivas_detalhe":len(set(d)-set(b)),
        "excecoes":len(differences),
        "secoes_inconsistentes_aptos_comparecimento_abstencoes":conserv,
        "totalizadores":[{"origem":k,"aptos":v[0],"comparecimento":v[1],"abstencoes":v[2]} for k,v in sums.items()],
    }
    (a.out/"manifesto_comparecimento_publico.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

if __name__=="__main__":
    main()
