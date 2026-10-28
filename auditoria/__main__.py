"""CLI do FATOVIA AUDITA: catalogo, uf e consolidar.

Uso: python -m auditoria uf --uf MA --out work/states/MA.json
     python -m auditoria consolidar --states work/states --out work/report
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

from .tse import (
    UFS, bu_resources, count_bu, count_official, download_zip, fetch,
    official_resource, resources, sha512_expected, DATASET_BU, DATASET_RESULTADOS,
)


def utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def audit_state(uf):
    result = {"uf": uf, "status": "ERRO", "gerado_em_utc": utc(),
              "fonte": "https://dadosabertos.tse.jus.br/dataset/" + DATASET_BU}
    try:
        catalog = resources(DATASET_BU)
        bu, checksum = bu_resources(uf, catalog)
        result["recurso_id"] = bu["id"]
        result["url"] = bu["url"]
        result["url_sha512"] = checksum["url"]
        expected = sha512_expected(checksum["url"])
        with tempfile.TemporaryDirectory(prefix="fatovia-bu-") as tmp:
            digest, size = download_zip(bu["url"], Path(tmp) / "bu.zip")
            result.update({"sha512_publicado": expected, "sha512_calculado": digest,
                           "bytes_zip": size, "hash_conferido": digest == expected})
            if digest != expected:
                raise ValueError("Hash SHA512 do ZIP diferente do publicado pelo TSE")
            counts = count_bu(uf, Path(tmp) / "bu.zip")
        result.update(counts)
    except Exception as exc:
        result["status"] = "ERRO"
        result["erro"] = f"{type(exc).__name__}: {exc}"
    return result


def reference_totals():
    source = official_resource(resources(DATASET_RESULTADOS))
    info = {"recurso_id": source["id"], "url": source["url"],
            "fonte": "https://dadosabertos.tse.jus.br/dataset/" + DATASET_RESULTADOS}
    with tempfile.TemporaryDirectory(prefix="fatovia-ref-") as tmp:
        path = Path(tmp) / "referencia.zip"
        digest, size = download_zip(source["url"], path)
        counted = count_official(path)
    info["sha512_calculado"] = digest
    info["bytes_zip"] = size
    return counted, info


def consolidate(states_dir, *, reference_loader=reference_totals):
    states_dir = Path(states_dir)
    raw = {}
    issues = []
    for file in sorted(states_dir.glob("*.json")):
        obj = json.loads(file.read_text(encoding="utf-8"))
        uf = obj.get("uf")
        if uf not in UFS or uf in raw or file.stem.upper() != uf:
            issues.append({"tipo": "arquivo_uf_invalido_ou_duplicado", "arquivo": file.name})
        else:
            raw[uf] = obj
    absent = sorted(set(UFS) - set(raw))
    status_bad = sorted(x for x, r in raw.items()
                        if r.get("status") != "OK" or r.get("hash_conferido") is not True)
    totals = Counter()
    by_uf = {}
    for uf, state in raw.items():
        if state.get("status") != "OK" or state.get("hash_conferido") is not True:
            continue
        parsed = {str(v): int(n) for v, n in state["votos"].items()}
        by_uf[uf] = parsed
        totals.update(parsed)
    comparison = []
    ref = {}
    if not absent and not status_bad and not issues:
        try:
            expected, ref = reference_loader()
            for uf in UFS:
                keys = set(by_uf[uf]) | {v for u, v in expected if u == uf}
                for candidate in sorted(keys):
                    actual = by_uf[uf].get(candidate, 0)
                    official = expected.get((uf, candidate), 0)
                    if actual != official:
                        comparison.append({"uf": uf, "votavel": candidate,
                                           "bu": actual, "referencia": official,
                                           "diferenca": actual - official})
            official_ufs = {u for u, _ in expected}
            if set(UFS) != official_ufs:
                issues.append({"tipo": "referencia_sem_cobertura",
                               "ufs_ausentes": sorted(set(UFS) - official_ufs)})
        except Exception as exc:
            issues.append({"tipo": "referencia_indisponivel",
                           "detalhes": f"{type(exc).__name__}: {exc}"})
    if absent or status_bad or issues:
        status = "INCONCLUSIVO"
    elif comparison:
        status = "DIVERGENCIAS_DE_TOTALIZACAO"
    else:
        status = "CONFERENCIA_CONSISTENTE"
    return {
        "projeto": "FATOVIA AUDITA",
        "pleito": "Eleições 2026, segundo turno, Presidente",
        "gerado_em_utc": utc(),
        "status": status,
        "ressalva": ("Conferência de consistência entre duas bases publicadas pelo próprio TSE. "
                     "Não comprova ausência de fraude, autenticidade de cada BU impresso, "
                     "nem correspondência entre voto e intenção do eleitor."),
        "ufs_esperadas": len(UFS), "ufs_recebidas": len(raw),
        "ufs_com_bu_e_hash_validos": len(by_uf),
        "ufs_ausentes": absent, "ufs_com_erro": status_bad,
        "total_secoes_conferidas": sum(raw[uf].get("secoes", 0) for uf in by_uf),
        "totais_recontados_por_numero": dict(sorted(totals.items())),
        "diferencas_com_referencia": comparison,
        "ocorrencias": issues,
        "referencia": ref,
        "arquivos_por_uf": raw,
    }


def markdown_report(report):
    label = {
        "CONFERENCIA_CONSISTENTE": "Conferência consistente entre as bases",
        "DIVERGENCIAS_DE_TOTALIZACAO": "Divergências a investigar",
        "INCONCLUSIVO": "Inconclusivo: sem validação integral",
    }[report["status"]]
    lines = [
        "# FATOVIA AUDITA | Segundo turno 2026",
        "", f"**Status: {label}.**", "",
        f"Gerado em UTC: {report['gerado_em_utc']}",
        f"UFs com arquivo íntegro e conferido: **{report['ufs_com_bu_e_hash_validos']}/{report['ufs_esperadas']}**.",
        f"Seções conferidas: **{report['total_secoes_conferidas']}**.", "",
        "## Recontagem dos BUs por número do votável",
        "", "| Número | Votos |", "|---|---:|",
    ]
    for candidate, count in report["totais_recontados_por_numero"].items():
        lines.append(f"| {candidate} | {count:,} |".replace(",", "."))
    lines.extend(["", "Os códigos não equivalem automaticamente a votos válidos; "
                  "brancos e nulos podem aparecer como números próprios.",
                  "", "## Alertas e divergências", ""])
    if report["ufs_ausentes"]:
        lines.append("**UFs ausentes:** " + ", ".join(report["ufs_ausentes"]))
    if report["ufs_com_erro"]:
        lines.append("**UFs sem conferência íntegra:** " + ", ".join(report["ufs_com_erro"]))
    for i in report["ocorrencias"][:40]:
        lines.append("- " + json.dumps(i, ensure_ascii=False))
    for i in report["diferencas_com_referencia"][:40]:
        lines.append("- Diferença entre bases: " + json.dumps(i, ensure_ascii=False))
    if not report["ocorrencias"] and not report["diferencas_com_referencia"] and not report["ufs_com_erro"]:
        lines.append("Nenhuma diferença detectada nas verificações executadas.")
    lines.extend([
        "", "## Escopo, limites e reprodução", "",
        report["ressalva"], "",
        "- Fonte dos boletins: https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna",
        "- Comparação: https://dadosabertos.tse.jus.br/dataset/resultados-2026",
        "- A conferência SHA512 verifica identidade com o hash publicado pelo TSE, "
        "não autenticidade independente dos dados.",
        "- O relatório completo em JSON inclui URLs, SHA512, status e amostras de ocorrências por UF.",
        "- Falhas e diferenças exigem investigação documental, não equivalem a fraude comprovada.",
        "",
    ])
    return "\n".join(lines)


def main():
    cli = argparse.ArgumentParser(description="FATOVIA AUDITA / recontagem 2º turno 2026")
    commands = cli.add_subparsers(dest="command", required=True)
    state_cmd = commands.add_parser("uf")
    state_cmd.add_argument("--uf", required=True, choices=UFS)
    state_cmd.add_argument("--out", required=True)
    report_cmd = commands.add_parser("consolidar")
    report_cmd.add_argument("--states", default="work/states")
    report_cmd.add_argument("--out", default="work/report")
    commands.add_parser("catalogo")
    args = cli.parse_args()
    if args.command == "catalogo":
        catalog = resources(DATASET_BU)
        for uf in UFS:
            b, s = bu_resources(uf, catalog)
            print(f"{uf}: {b['url']} | SHA512: {s['url']}")
    elif args.command == "uf":
        result = audit_state(args.uf)
        save(args.out, result)
        print(f"{args.uf}: {result['status']} | {args.out}")
        if result["status"] == "ERRO":
            print(result.get("erro", "Erro desconhecido"))
    else:
        report = consolidate(args.states)
        target = Path(args.out)
        save(target / "relatorio.json", report)
        (target / "relatorio.md").write_text(markdown_report(report), encoding="utf-8")
        print(f"Relatório: {report['status']} | {target}")
        # Falha final é deliberada: proíbe marcar a auditoria inconclusiva como sucesso.
        if report["status"] != "CONFERENCIA_CONSISTENTE":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
