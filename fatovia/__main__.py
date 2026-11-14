"""Comandos: python -m fatovia scan | report | demo (publicação externa DESLIGADA)."""
import argparse
import json
from pathlib import Path

from .engine import choose, load, now_local, rollup_report, save, scan_camara, from_camara, fresh_stage, validate_candidate
from .evidence import seal, sealed
from datetime import datetime, timedelta
from .render import render
from .analytics import pull_metrics

STATE = Path("data/state.json")
REPORT = Path("data/last_report.json")


def main():
    parser = argparse.ArgumentParser(description="FatoVia: radar documental seguro")
    parser.add_argument("command", choices=("scan", "report", "demo", "metrics"))
    command = parser.parse_args().command
    state = load(STATE)
    now = now_local()
    if command == "metrics":
        result = pull_metrics(state)
        save(STATE, state)
        print(json.dumps(result, ensure_ascii=False))
        return
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
    diagnostics = {}
    # Do not remove a candidate matching an unresolved publication transaction.
    tx = state.get("publishing") or {}
    old_pending = state.get("pending", [])
    state["pending"] = [p for p in old_pending if
        (p.get("id"),p.get("version")) == (tx.get("id"),tx.get("version"))
        or (not validate_candidate(p) and fresh_stage(p,now) and sealed(p,now))]
    diagnostics["expired_or_unsealed_removed"] = len(old_pending)-len(state["pending"])
    selection_state = dict(state)
    try:
        discovery = load("data/discovery_report.json")
        observed = datetime.fromisoformat(discovery["generated_at"])
        if now-timedelta(hours=48)<=observed<=now:
            selection_state["discovery_topic_groups"] = discovery.get("topic_groups",[])
    except (OSError, ValueError, KeyError,TypeError):
        pass
    try:
        candidates = scan_camara(now, diagnostics=diagnostics)
    except Exception as exc:
        candidates = []
        errors.append(f"Radar indisponível ({type(exc).__name__})")
    # Limite de armazenamento e de produção: não acumular imagens sem controle.
    slots = max(0, 8 - len(state.get("pending", [])))
    chosen = choose(candidates, selection_state, now, maximum=min(4, slots))
    staged = 0
    for item in chosen:
        try:
            render(item)
            seal(item, now)
            item["status"] = "ready"
            state.setdefault("pending", []).append(item)
            staged += 1
        except Exception as exc:
            errors.append(f'Falha no card {item["id"]}: {type(exc).__name__}')
    report = rollup_report(state, now, len(candidates), staged)
    report["errors"] = errors
    report["scan_diagnostics"] = diagnostics
    report["selected"] = [{"id":x["id"],"score":x["editorial_score"],"discover_sources":x.get("discovery_source_count",0),"explore":x.get("explore_signal_count",0)} for x in chosen]
    # Apenas imagens prontas, geradas dentro de docs/media. Nenhuma credencial no catálogo público.
    catalog = []
    for item in state.get("pending", [])[:8]:
        cards = item.get("cards", [])
        if item.get("status") != "ready" or len(cards) != 7:
            continue
        paths = [Path(path) for path in cards]
        try:
            urls = [str(path.relative_to("docs")).replace("\\", "/") for path in paths]
            if not all(url.startswith("media/") and ".." not in url for url in urls):
                continue
        except ValueError:
            continue
        catalog.append({"title": item.get("title", "Documento"), "cards": urls})
    save(Path("docs/manifest.json"), {
        "schema": 1,
        "items": catalog,
        "note": "Preparacao editorial: a presenca de um JPEG nao representa publicacao no Instagram."
    })
    save(STATE, state)
    save(REPORT, report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
