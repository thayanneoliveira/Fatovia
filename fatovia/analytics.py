"""Coleta opcional de métricas Meta; sem token, parâmetros ficam conservadores.

O token deve ser cadastrado apenas em GitHub Actions Secrets.
"""
import os
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Fortaleza")


def pull_metrics(state):
    token = os.environ.get("META_ACCESS_TOKEN", "")
    if not token:
        return {"updated": 0, "reason": "Sem credenciais; sem atualização de métricas"}
    version = os.environ.get("META_GRAPH_VERSION", "v25.0")
    if not version.startswith("v") or not version[1:].replace(".", "").isdigit():
        return {"updated": 0, "reason": "Versão de API inválida"}
    host = (os.getenv("META_API_HOST") or "graph.instagram.com").strip().lower()
    if host not in {"graph.instagram.com", "graph.facebook.com"}:
        return {"updated": 0, "reason": "Host Meta inválido"}
    import requests
    by_media = {str(row.get("media_id")): row for row in state.get("metrics", [])}
    updated = 0
    errors = 0
    for post in state.get("published", [])[-80:]:
        mid = post.get("media_id")
        if not mid:
            continue
        try:
            response = requests.get(
                f"https://{host}/{version}/{mid}/insights",
                headers={"Authorization": f"Bearer {token}"},
                params={"metric": "reach,saved,shares"},
                timeout=25,
            )
            response.raise_for_status()
            data = response.json().get("data", [])
            values = {}
            for metric in data:
                series = metric.get("values")
                if series and isinstance(series, list):
                    value = series[0].get("value")
                else:
                    value = metric.get("total_value", {}).get("value")
                if isinstance(value, (int, float)):
                    values[metric["name"]] = int(value)
            if "reach" not in values:
                continue
            dt = datetime.fromisoformat(post["published_at"].replace("Z", "+00:00"))
            by_media[str(mid)] = {
                "media_id": str(mid),
                "reach": values["reach"],
                "shares": values.get("shares", 0),
                "saves": values.get("saved", 0),
                "hour": dt.astimezone(TZ).hour,
            }
            updated += 1
        except (ValueError, KeyError, requests.RequestException):
            errors += 1
    state["metrics"] = list(by_media.values())
    return {"updated": updated, "errors": errors, "note": "Dados podem chegar com atraso"}
