#!/usr/bin/env python3
"""Reconciliação documental estrita por seção (não é auditoria de conteúdo do voto).

Usa somente arquivos oficiais previamente adquiridos e seus .sha512, SEM baixar dados.
As diferenças são inventário de hipóteses; não são prova de substituição irregular.
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path

UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO ZZ".split()
PATTERNS = {
    "24": "CESP_2t_{uf}_241020261231.zip",
    "25": "CESP_2t_{uf}_251020261345.zip",
    "efetivada": "CEFT_2t_{uf}_261020261201.zip",
    "bu": "bweb_2t_{uf}_261020260742.zip",
}
PAIRS = [("24", "25"), ("25", "efetivada"), ("efetivada", "bu")]
KEYS = {
    "municipio": ["CD_MUNICIPIO", "CD_MUN", "NR_MUNICIPIO"],
    "zona": ["NR_ZONA", "ZONA"],
    "secao": ["NR_SECAO", "SECAO"],
    "urna": ["NR_URNA", "NR_SERIE_URNA", "NR_URNA_EFETIVADA", "NR_URNA_ESPERADA", "NR_EQUIPAMENTO"],
}
SHA = re.compile(r"\\b[a-fA-F0-9]{128}\\b")

class IncompleteAudit(RuntimeError):
    pass

def digest(path):
    h = hashlib.sha512()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()

def verify_source(path):
    if not path.is_file():
        raise IncompleteAudit("arquivo ausente: " + str(path))
    ref = Path(str(path) + ".sha512")
    if not ref.is_file():
        raise IncompleteAudit("referência .sha512 ausente: " + str(ref))
    raw = ref.read_bytes()
    if zipfile.is_zipfile(io.BytesIO(raw)):
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names = [n for n in z.namelist() if not n.endswith("/")]
            if len(names) != 1:
                raise IncompleteAudit("referência compactada ambígua: " + str(ref))
            raw = z.read(names[0])
    hs = set(x.lower() for x in SHA.findall(raw.decode("utf-8-sig", errors="replace")))
    if len(hs) != 1:
        raise IncompleteAudit("hash oficial ausente ou ambíguo: " + str(ref))
    actual = digest(path)
    if actual != next(iter(hs)):
        raise IncompleteAudit("SHA-512 não confere: " + str(path))
    return actual

def normal(s):
    s = str(s if s is not None else "").strip()
    if not s:
        return ""
    return str(int(s)) if s.isdecimal() else s

def col(cols, variants):
    available = {re.sub(r"[^A-Z0-9]", "", x.upper()): x for x in cols}
    return next((available[z] for v in variants if (z := re.sub(r"[^A-Z0-9]", "", v.upper())) in available), None)

def parse_zip(path, source):
    """Aceita apenas CSVs de seção; ccont (reserva/contingência) não possui coluna seção."""
    index, rows, ignored, parsed = {}, 0, [], []
    with zipfile.ZipFile(path) as z:
        members = [m for m in z.infolist() if not m.is_dir() and m.filename.lower().endswith(".csv")]
        if not members:
            raise IncompleteAudit("ZIP sem arquivos CSV: " + str(path))
        for m in members:
            # Arquivo ccont representa reserva por zona, não seção; preservar no manifesto.
            if Path(m.filename).name.lower().startswith("ccont_"):
                ignored.append({"file": m.filename, "reason": "inventário de contingência sem chave de seção"})
                continue
            if m.file_size > 2 * 1024**3:
                raise IncompleteAudit("membro excede limite de tamanho: " + m.filename)
            with z.open(m) as handle:
                text = io.TextIOWrapper(handle, encoding="latin-1", errors="strict", newline="")
                header = text.readline()
                if not header:
                    raise IncompleteAudit("CSV vazio: " + m.filename)
                sep = max((";", ",", "\\t"), key=lambda x: header.count(x))
                names = next(csv.reader([header], delimiter=sep))
                fields = {k: col(names, variants) for k, variants in KEYS.items()}
                if not all(fields.values()):
                    raise IncompleteAudit("colunas obrigatórias ausentes em " + m.filename + ": " + str(fields))
                parsed.append(m.filename)
                for row in csv.DictReader(text, fieldnames=names, delimiter=sep):
                    rows += 1
                    key = tuple(normal(row.get(fields[k])) for k in ("municipio", "zona", "secao"))
                    urn = normal(row.get(fields["urna"]))
                    if not all(key) or not urn:
                        raise IncompleteAudit(f"chave/urna vazia em {m.filename}, registro {rows}")
                    old = index.setdefault(key, urn)
                    if old != urn:
                        raise IncompleteAudit(f"duas urnas para a mesma seção em {m.filename}: {key} ({old} vs {urn})")
    if not parsed or not index:
        raise IncompleteAudit("nenhuma seção válida processada em " + str(path))
    return index, {"rows": rows, "sections": len(index), "parsed_files": parsed, "ignored_files": ignored}

def compare(uf, name1, name2, a, b):
    out = []
    for key in sorted(set(a) | set(b), key=lambda x: tuple(int(y) if y.isdecimal() else y for y in x)):
        old, new = a.get(key, ""), b.get(key, "")
        if old == new:
            continue
        kind = ("somente_posterior" if not old else "somente_anterior" if not new else "urna_divergente")
        out.append({
            "uf": uf, "comparacao": name1 + "_vs_" + name2,
            "municipio": key[0], "zona": key[1], "secao": key[2],
            "urna_anterior": old, "urna_posterior": new, "tipo": kind,
            "status": "PENDENTE_DOCUMENTACAO", "ocorrencia_id": "",
            "ato_autorizacao": "", "ata_uri": "", "causa_documentada": "",
            "confianca_conclusao": "NAO_AVALIADA",
        })
    return out

def run(root, out, ufs):
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "2.0", "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": "ZIPs e referências .sha512 locais provenientes de distribuição TSE",
        "limitation": "SHA concordante com referência TSE não autentica independentemente a origem; não valida voto",
        "scope_requested": ufs, "status": "INCOMPLETE", "sources": {}, "errors": [], "coverage": {},
    }
    diffs = []
    for uf in ufs:
        indexes = {}
        for source, pattern in PATTERNS.items():
            path = root / pattern.format(uf=uf)
            try:
                sha = verify_source(path)
                index, metrics = parse_zip(path, source)
                indexes[source] = index
                manifest["sources"][uf + "/" + source] = {"file": path.name, "sha512": sha, **metrics}
            except (OSError, UnicodeError, ValueError, zipfile.BadZipFile, IncompleteAudit) as e:
                manifest["errors"].append({"uf": uf, "source": source, "reason": str(e)})
        if len(indexes) != 4:
            manifest["coverage"][uf] = {"status": "BLOCKED"}
            continue
        current = []
        for left, right in PAIRS:
            rows = compare(uf, left, right, indexes[left], indexes[right])
            current.extend(rows)
            counts = {k: sum(v["tipo"] == k for v in rows) for k in
                      ("urna_divergente", "somente_anterior", "somente_posterior")}
            manifest["coverage"][uf + "/" + left + "_vs_" + right] = {
                "status": "COMPLETE", "sections_left": len(indexes[left]),
                "sections_right": len(indexes[right]), **counts,
            }
        diffs.extend(current)
    # Não emitir CSV de 'resultado final' em presença de falhas; guardar diagnóstico apenas.
    if not manifest["errors"] and len(manifest["sources"]) == len(ufs) * 4:
        manifest["status"] = "COMPLETE_FOR_IDENTIFIER_COMPARISONS"
        destination = out / "matriz_completa_secoes.csv"
        columns = ["uf", "comparacao", "municipio", "zona", "secao", "urna_anterior",
                   "urna_posterior", "tipo", "status", "ocorrencia_id", "ato_autorizacao",
                   "ata_uri", "causa_documentada", "confianca_conclusao"]
        with destination.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(diffs)
        manifest["matrix_sha512"] = digest(destination)
        manifest["matrix_rows"] = len(diffs)
    (out / "manifesto_validacao.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\\n", encoding="utf-8"
    )
    return 0 if manifest["status"].startswith("COMPLETE") else 2

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--ufs", nargs="+", default=UFS, choices=UFS)
    args = p.parse_args()
    sys.exit(run(args.input_dir, args.output_dir, args.ufs))

if __name__ == "__main__":
    main()
