#!/usr/bin/env python3
"""Audita a CONTABILIDADE de um relatório legado; não revalida arquivos eleitorais."""
import argparse
import csv
import datetime as dt
import json
from collections import Counter
from pathlib import Path

UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO ZZ".split()
PAIRS = ["24_vs_25", "25_vs_efetivada", "efetivada_vs_bu"]
SOURCES = ["24", "25", "efetivada", "bu"]

def inspect(report):
    errors, warnings, evidence = [], [], []
    totals = {name: Counter() for name in PAIRS}
    states = report.get("states", {})
    if set(states) != set(UFS):
        errors.append(f"cobertura geográfica diferente de 28 unidades: {sorted(set(UFS) ^ set(states))}")
    for uf in UFS:
        st = states.get(uf)
        if not st:
            continue
        for source in SOURCES:
            src = st.get("sources", {}).get(source)
            if not src:
                errors.append(f"{uf}/{source}: fonte ausente")
                continue
            if src.get("sha512_status") != "MATCH":
                errors.append(f"{uf}/{source}: SHA não validado no legado")
            if src.get("error") or src.get("conflicts", 0):
                errors.append(f"{uf}/{source}: erro de coleta/parsing ou conflito de identificadores")
            if not src.get("sections") or not src.get("rows") or not src.get("members"):
                errors.append(f"{uf}/{source}: denominador, linhas ou membros ausentes")
        for pair in PAIRS:
            p = st.get("comparisons", {}).get(pair, {})
            if not all(isinstance(p.get(k), int) and p[k] >= 0 for k in
                       ["sections_previous", "sections_next", "only_previous", "only_next", "urn_id_different"]):
                errors.append(f"{uf}/{pair}: denominadores ou contagens inválidas")
                continue
            if p["urn_id_different"] > min(p["sections_previous"] - p["only_previous"],
                                          p["sections_next"] - p["only_next"]):
                errors.append(f"{uf}/{pair}: divergências maiores que a interseção")
            for k in ["sections_previous", "sections_next", "only_previous", "only_next", "urn_id_different"]:
                totals[pair][k] += p[k]
            for kind, sample_key, count_key in [
                ("urna_divergente", "examples_different", "urn_id_different"),
                ("somente_anterior", "examples_only_previous", "only_previous"),
                ("somente_posterior", "examples_only_next", "only_next")]:
                sample = p.get(sample_key, [])
                if len(sample) > p[count_key]:
                    errors.append(f"{uf}/{pair}/{kind}: exemplos excedem total")
                if len(sample) < p[count_key]:
                    warnings.append(f"{uf}/{pair}/{kind}: amostra parcial ({len(sample)}/{p[count_key]})")
                for x in sample:
                    if isinstance(x, dict):
                        mun, zone, sec, old, new = (x.get(k, "") for k in ("mun", "zona", "secao", "urn_old", "urn_new"))
                    else:
                        mun, zone, sec = (list(x) + ["", "", ""])[:3]
                        old = new = ""
                    evidence.append({
                        "uf": uf, "comparacao": pair, "municipio": mun, "zona": zone, "secao": sec,
                        "urna_anterior": old, "urna_posterior": new, "tipo": kind,
                        "proveniencia": "exemplo de relatório legado; NÃO é população total",
                        "status": "PENDENTE_DOCUMENTACAO",
                    })
    expected = {"24_vs_25": (350, 0, 12),
                "25_vs_efetivada": (2686, 0, 29),
                "efetivada_vs_bu": (0, 0, 0)}
    for pair, (diff, older, newer) in expected.items():
        a = totals[pair]
        if (a["urn_id_different"], a["only_previous"], a["only_next"]) != (diff, older, newer):
            errors.append(f"{pair}: totais distintos do relatório nacional conhecido")
    return {
        "status": "METADADOS_CONSISTENTES_NAO_REEXECUTADOS" if not errors else "INCONSISTENTE",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_run_utc": report.get("run_utc"),
        "limitation": "Esta revisão usa metadados do resultado anterior; não reproduz SHA nem parseia ZIPs.",
        "observations": {
            "inclusoes_24_25": totals["24_vs_25"]["only_next"],
            "inclusoes_25_efetivada": totals["25_vs_efetivada"]["only_next"],
            "confronto_efetivada_bu_urnas_diferentes": totals["efetivada_vs_bu"]["urn_id_different"],
        },
        "totals": {k: dict(v) for k, v in totals.items()},
        "sample_rows": len(evidence), "warnings": warnings, "errors": errors,
    }, evidence

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    result, samples = inspect(json.loads(a.report.read_text(encoding="utf-8")))
    (a.out / "revisao_legado.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (a.out / "amostra_legado_NAO_CENSITARIA.csv").open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["uf", "comparacao", "municipio", "zona", "secao", "urna_anterior",
                      "urna_posterior", "tipo", "proveniencia", "status"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(samples)
    print(json.dumps({"status": result["status"], "observations": result["observations"],
                      "sample_rows": len(samples), "warnings": len(result["warnings"]),
                      "errors": result["errors"]}, ensure_ascii=False))
    raise SystemExit(0 if not result["errors"] else 2)

if __name__ == "__main__":
    main()
