#!/usr/bin/env python3
"""Consolida matrizes locais de 28 UFs sem aceitar omissões silenciosas."""
import argparse
import csv
import datetime as dt
import hashlib
import json
from collections import Counter
from pathlib import Path
from importlib.machinery import SourceFileLoader
audit = SourceFileLoader("audit", str(Path(__file__).with_name("reconciliar_secoes.py"))).load_module()
EXPECTED = {
    "24_vs_25": {"urna_divergente": 350, "somente_anterior": 0, "somente_posterior": 12},
    "25_vs_efetivada": {"urna_divergente": 2686, "somente_anterior": 0, "somente_posterior": 29},
    "efetivada_vs_bu": {"urna_divergente": 0, "somente_anterior": 0, "somente_posterior": 0},
}
def sha(path):
    return hashlib.sha512(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary = {"run_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
               "status": "INCOMPLETE", "errors": [], "shards": [],
               "counts": {}, "limitation": "Confronto de identificadores. NÃO valida conteúdo do voto."}
    all_ufs, rows, head = set(), [], None
    for mf in sorted(args.input_dir.rglob("manifesto_validacao.json")):
        m = json.loads(mf.read_text(encoding="utf-8"))
        shard_ufs = set(m.get("scope_requested", []))
        if all_ufs & shard_ufs:
            summary["errors"].append(f"UF repetida em {mf}: {all_ufs & shard_ufs}")
        all_ufs |= shard_ufs
        if m.get("status") != "COMPLETE_FOR_IDENTIFIER_COMPARISONS" or m.get("errors"):
            summary["errors"].append(f"shard incompleto: {mf}")
            continue
        matrix = mf.with_name("matriz_completa_secoes.csv")
        if not matrix.is_file() or sha(matrix) != m.get("matrix_sha512"):
            summary["errors"].append(f"matriz ausente ou checksum incorreto: {matrix}")
            continue
        with matrix.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if head is None:
                head = reader.fieldnames
            elif head != reader.fieldnames:
                summary["errors"].append(f"cabeçalhos divergentes em {matrix}")
            part = list(reader)
        if len(part) != m.get("matrix_rows"):
            summary["errors"].append(f"número de linhas não confere: {matrix}")
        if set(x["uf"] for x in part) - shard_ufs:
            summary["errors"].append(f"matriz contém UF fora do shard: {matrix}")
        rows.extend(part)
        summary["shards"].append({"manifest": str(mf), "ufs": sorted(shard_ufs),
                                   "matrix_sha512": sha(matrix), "rows": len(part)})
    if all_ufs != set(audit.UFS):
        summary["errors"].append(f"cobertura das UFs incompleta: {sorted(set(audit.UFS) - all_ufs)}")
    if len(summary["shards"]) != 4:
        summary["errors"].append("esperados exatamente quatro shards íntegros")
    counter = Counter((r["comparacao"], r["tipo"]) for r in rows)
    for pair, expected in EXPECTED.items():
        summary["counts"][pair] = {}
        for typ, v in expected.items():
            observed = counter[pair, typ]
            summary["counts"][pair][typ] = observed
            if v != observed:
                summary["errors"].append(f"{pair}/{typ}: observado {observed}, legado {v}; requer investigação")
    summary["total_matrix_rows"] = len(rows)
    if not summary["errors"]:
        destination = args.output_dir / "matriz_nacional_completa.csv"
        with destination.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=head)
            writer.writeheader()
            writer.writerows(sorted(rows, key=lambda r: (r["uf"], r["comparacao"],
                      int(r["municipio"]), int(r["zona"]), int(r["secao"]))))
        summary["matrix_sha512"] = sha(destination)
        summary["status"] = "COMPLETE_FOR_IDENTIFIER_COMPARISONS_ONLY"
    (args.output_dir / "resumo_nacional_v2.json").write_text(
       json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    raise SystemExit(0 if not summary["errors"] else 2)

if __name__ == "__main__":
    main()
