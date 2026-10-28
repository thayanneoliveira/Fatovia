"""Leitor reprodutível dos BUs publicados pelo TSE (eleições 2026, 2º turno).

A fonte é o Portal de Dados Abertos (SISTOT); não são BUs coletados
independentemente nas seções. Falha de formato, cobertura ou hash bloqueia
a conclusão positiva.
"""
from __future__ import annotations

import csv
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import time
import unicodedata
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import zipfile

DATASET_BU = "resultados-2026-boletim-de-urna"
DATASET_RESULTADOS = "resultados-2026"
API = "https://dadosabertos.tse.jus.br/api/3/action/package_show?id="
UFS = tuple("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO ZZ".split())
MAX_ZIP_BYTES = 1_500_000_000
MAX_CSV_BYTES = 6_000_000_000


def normal(text):
    text = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in text if not unicodedata.combining(c)).casefold()


def fetch(url, *, max_bytes=5_000_000):
    """GET com limite de bytes, timeout e retentativas curtas."""
    if urlparse(url).scheme != "https":
        raise ValueError("URL não HTTPS")
    last = None
    for i in range(3):
        try:
            req = Request(url, headers={"User-Agent": "FatoViaAudita/1.0 (dados publicos)"})
            with urlopen(req, timeout=90) as response:
                data = response.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise ValueError("Resposta excedeu o limite de bytes")
                return data
        except (OSError, TimeoutError) as exc:
            last = exc
            if i < 2:
                time.sleep(2 ** i)
    raise RuntimeError(f"Falha de download: {url}: {last}")


def resources(dataset):
    obj = json.loads(fetch(API + dataset))
    if obj.get("success") is not True:
        raise ValueError("API CKAN não confirmou sucesso")
    result = obj.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("resources"), list):
        raise ValueError("Metadados CKAN inválidos")
    return result["resources"]


def bu_resources(uf, all_resources):
    """Seleciona precisamente os links oficiais do 2º turno e mesma UF."""
    if uf not in UFS:
        raise ValueError("UF inválida")
    filtered = [r for r in all_resources
                if re.match(r"^" + uf + r"\s*-", str(r.get("name", "")), re.I)
                and ("segundo turno" in normal(r["name"]) or "2o turno" in normal(r["name"]))]
    bu = [r for r in filtered if "boletim de urna" in normal(r["name"])]
    digest = [r for r in filtered if "hash sha2" in normal(r["name"])]
    if len(bu) != 1 or len(digest) != 1:
        raise ValueError(f"{uf}: esperado 1 BU e 1 SHA2; encontrados {len(bu)} e {len(digest)}")
    for r in (bu[0], digest[0]):
        parsed = urlparse(r.get("url", ""))
        if parsed.scheme != "https" or parsed.hostname != "cdn.tse.jus.br":
            raise ValueError(f"{uf}: URL de recurso não autorizada")
    if not bu[0]["url"].endswith(".zip") or not digest[0]["url"].endswith(".zip.sha512"):
        raise ValueError(f"{uf}: extensões BU e SHA512 inesperadas")
    if digest[0]["url"] != bu[0]["url"] + ".sha512":
        raise ValueError(f"{uf}: SHA512 não corresponde ao arquivo ZIP")
    return bu[0], digest[0]


def download_zip(url, target):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    h = hashlib.sha512()
    total = 0
    try:
        req = Request(url, headers={"User-Agent": "FatoViaAudita/1.0 (dados publicos)"})
        with urlopen(req, timeout=180) as response, tmp.open("wb") as output:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > MAX_ZIP_BYTES:
                    raise ValueError("ZIP excede limite de segurança")
                h.update(block)
                output.write(block)
        if not zipfile.is_zipfile(tmp):
            raise ValueError("Recurso baixado não é ZIP válido")
        tmp.replace(target)
        return h.hexdigest(), total
    finally:
        tmp.unlink(missing_ok=True)


def sha512_expected(url):
    doc = fetch(url, max_bytes=100_000).decode("ascii", errors="strict")
    # TSE publica .zip.sha512 como texto hexadecimal, eventualmente com nome.
    matches = re.findall(r"(?<![a-fA-F0-9])[a-fA-F0-9]{128}(?![a-fA-F0-9])", doc)
    unique = set(x.lower() for x in matches)
    if len(unique) != 1:
        raise ValueError("SHA512 publicado não contém exatamente um digest inequívoco")
    return unique.pop()


def csv_rows(path):
    """Leitura streaming de 1 CSV no ZIP, sem descompactar para o disco."""
    with zipfile.ZipFile(path) as archive:
        names = [f for f in archive.infolist()
                 if not f.is_dir() and f.filename.lower().endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"Esperado 1 CSV no ZIP; encontrados {len(names)}")
        info = names[0]
        if info.file_size > MAX_CSV_BYTES:
            raise ValueError("CSV descompactado excede limite de segurança")
        with archive.open(info, "r") as sample:
            prefix = sample.read(8192)
        try:
            prefix.decode("utf-8-sig")
            encoding = "utf-8-sig"
        except UnicodeDecodeError:
            encoding = "latin-1"
        with archive.open(info, "r") as raw:
            with io.TextIOWrapper(raw, encoding=encoding, errors="strict", newline="") as stream:
                reader = csv.DictReader(stream, delimiter=";")
                if not reader.fieldnames:
                    raise ValueError("CSV sem cabeçalho")
                reader.fieldnames = [x.strip().lstrip("\ufeff").upper() for x in reader.fieldnames]
                for row in reader:
                    yield {str(k).upper(): (v or "").strip() for k, v in row.items()}


def number(value, label):
    if not re.fullmatch(r"\d+", str(value)):
        raise ValueError(f"Campo numérico inválido: {label}={value!r}")
    return int(value)


def count_bu(uf, archive):
    """Soma apenas votos para Presidente, mantendo identidade por seção/votável."""
    required = {"NR_TURNO", "SG_UF", "CD_MUNICIPIO", "NR_ZONA",
                "NR_SECAO", "NR_VOTAVEL", "QT_VOTOS"}
    voters = {}
    vote_seen = set()
    votes = Counter()
    issues = []
    total_rows = 0
    pres_rows = 0
    section_votes = Counter()
    for row in csv_rows(archive):
        total_rows += 1
        if total_rows == 1 and not required.issubset(row):
            raise ValueError(f"Colunas BU ausentes: {sorted(required - set(row))}")
        if row["NR_TURNO"] != "2":
            continue
        is_president = row.get("CD_CARGO_PERGUNTA", "") == "1" or normal(row.get("DS_CARGO_PERGUNTA", "")) == "presidente"
        if not is_president:
            continue
        pres_rows += 1
        if row["SG_UF"].upper() != uf:
            raise ValueError(f"UF divergente dentro de {uf}: {row['SG_UF']}")
        section = (uf, row["CD_MUNICIPIO"], row["NR_ZONA"], row["NR_SECAO"])
        votable = row["NR_VOTAVEL"]
        key = section + (votable,)
        count = number(row["QT_VOTOS"], "QT_VOTOS")
        if key in vote_seen:
            if len(issues) < 100:
                issues.append({"tipo": "votavel_duplicado", "secao": section, "votavel": votable})
            continue  # nunca duplica votos ao contabilizar
        vote_seen.add(key)
        votes[votable] += count
        section_votes[section] += count
        turnout_raw = row.get("QT_COMPARECIMENTO", "")
        if turnout_raw:
            turnout = number(turnout_raw, "QT_COMPARECIMENTO")
            if section in voters and voters[section] != turnout:
                if len(issues) < 100:
                    issues.append({"tipo": "comparecimento_inconsistente", "secao": section})
            voters[section] = turnout
    if not pres_rows or not section_votes:
        raise ValueError("Nenhum voto de Presidente do 2º turno encontrado")
    if not voters:
        raise ValueError("Coluna QT_COMPARECIMENTO ausente: sem validação seção a seção")
    mismatch_count = 0
    for section, summed in section_votes.items():
        expected = voters.get(section)
        if expected is None or summed != expected:
            mismatch_count += 1
            if len(issues) < 100:
                issues.append({"tipo": "soma_secao_divergente", "secao": section,
                               "soma_votos": summed, "comparecimento": expected})
    return {"uf": uf, "status": "OK" if not issues and mismatch_count == 0 else "INCONSISTENTE",
            "linhas_csv": total_rows, "linhas_presidente_2t": pres_rows,
            "secoes": len(section_votes), "votos": dict(sorted(votes.items())),
            "total_votos": sum(votes.values()), "secoes_divergentes": mismatch_count,
            "ocorrencias_amostra": issues, "ocorrencias_amostra_truncada": len(issues) >= 100}


def official_resource(all_resources):
    found = [r for r in all_resources
             if "presidente" in normal(r.get("name", ""))
             and "votacao por secao eleitoral" in normal(r.get("name", ""))]
    if len(found) != 1:
        raise ValueError(f"Referência presidencial: esperado 1 recurso, encontrados {len(found)}")
    url = found[0].get("url", "")
    if urlparse(url).hostname != "cdn.tse.jus.br" or not url.endswith(".zip"):
        raise ValueError("URL de votação presidencial inesperada")
    return found[0]


def count_official(path):
    """Comparação de segunda fonte publicada pelo TSE (não externa ao TSE)."""
    votes = {}
    rows = 0
    for row in csv_rows(path):
        rows += 1
        if rows == 1:
            required = {"NR_TURNO", "SG_UF", "NR_VOTAVEL", "QT_VOTOS"}
            if not required.issubset(row):
                raise ValueError(f"Colunas da referência ausentes: {sorted(required-set(row))}")
        if row["NR_TURNO"] != "2":
            continue
        uf = row["SG_UF"].upper()
        if uf not in UFS:
            raise ValueError(f"UF inesperada na referência: {uf}")
        k = (uf, row["NR_VOTAVEL"])
        votes[k] = votes.get(k, 0) + number(row["QT_VOTOS"], "QT_VOTOS")
    if not votes:
        raise ValueError("Referência sem dados do 2º turno")
    return votes
