"""Comandos: python -m fatovia scan | report | demo (publicação externa DESLIGADA)."""
import argparse
import json
from pathlib import Path

from .engine import choose, load, now_local, rollup_report, save, scan_camara, from_camara
from .render import render

STATE = Path("data/state.json")
REPORT = Path("data/last_report.json")


def main():
    parser = argparse.ArgumentParser(description="FatoVia: radar documental seguro")
    parser.add_argument("command", choices=("scan", "report", "demo"))
    command = parser.parse_args().command
    state = load(STATE)
    now = now_local()
    if command == "report":
        print(json.dumps(rollup_report(state, now, 0, 0), indent=2, ensure_ascii=False))
        return
    if command == "demo":
        record = {
            "id": 9999999, "siglaTipo": "TESTE", "numero": 1, "ano": 2026,
            "ementa": "Este conteúdo é um exemplo fictício, criado somente para testar a diagramação do FatoVia. "
                      "Não representa proposta legislativa, lei ou decisão política verdadeira."
        }
        item = from_camara(record, {
            "descricaoTramitacao": "Etapa fictícia usada exclusivamente no teste.",
            "dataHora": "2026-10-25",
        })
        item["topics"] = ["tecnologia"]
        render(item, "demo/cards")
        print(json.dumps({"cards": 7, "status": "DEMO", "publication": "DISABLED"}))
        return

    errors = []
    try:
        candidates = scan_camara(now)
    except Exception as exc:
        candidates = []
        errors.append(f"Radar indisponível ({type(exc).__name__})")
    # Limite de armazenamento e de produção: não acumular imagens sem controle.
    slots = max(0, 8 - len(state.get("pending", [])))
    chosen = choose(candidates, state, now, maximum=min(2, slots))
    staged = 0
    for item in chosen:
        try:
            render(item)
            item["status"] = "ready"
            state.setdefault("pending", []).append(item)
            staged += 1
        except Exception as exc:
            errors.append(f'Falha no card {item["id"]}: {type(exc).__name__}')
    report = rollup_report(state, now, len(candidates), staged)
    report["errors"] = errors
    save(STATE, state)
    save(REPORT, report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
