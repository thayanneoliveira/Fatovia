"""Radar editorial documental e seleção determinística. Não recomenda candidaturas."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Fortaleza")
TOPICS = {
    "saude": ["saúde", "sus", "hospital", "vacina", "medicamento", "consulta"],
    "educacao": ["educação", "escola", "universidade", "professor", "ensino"],
    "economia": ["orçamento", "imposto", "tribut", "renda", "salário", "despesa pública"],
    "seguranca": ["segurança pública", "violência", "polícia", "criminal"],
    "ambiente": ["meio ambiente", "clima", "desmatamento", "saneamento", "água"],
    "tecnologia": ["tecnologia", "dados pessoais", "inteligência artificial", "digital"],
    "infraestrutura": ["transporte", "energia", "habitação", "moradia", "infraestrutura"],
}
ELECTORAL_APPEALS = ("vote em", "não vote em", "melhor candidato", "pior candidato", "apoie o candidato")


def now_local():
    return datetime.now(TZ)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, data):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:14]


def classify(text):
    lower = str(text).casefold()
    return [topic for topic, keys in TOPICS.items() if any(word in lower for word in keys)]


def from_camara(record, stage):
    rid = str(record["id"])
    summary = re.sub(r"\s+", " ", str(record.get("ementa") or "")).strip()
    title = f'{record.get("siglaTipo", "PROP")} {record.get("numero", "?")}/{record.get("ano", "?")}'
    stage_text = re.sub(r"\s+", " ", str(stage.get("descricaoTramitacao") or stage.get("despacho") or stage.get("siglaOrgao") or "")).strip()
    stage_date = str(stage.get("dataHora") or "")[:10]
    return {
        "id": f"camara:{rid}",
        "version": digest(summary + "\n" + stage_text + "\n" + stage_date),
        "title": title,
        "summary": summary,
        "summary_hash": digest(summary.casefold()),
        "source_url": f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{rid}",
        "public_url": f"https://www.camara.leg.br/propostas-legislativas/{rid}",
        "source_name": "Câmara dos Deputados",
        "stage": stage_text,
        "stage_date": stage_date,
        "topics": classify(summary),
        "status": "discovered",
    }


def validate_candidate(item):
    issues = []
    source = urlparse(item.get("source_url", ""))
    if not str(item.get("id", "")).startswith("camara:"):
        issues.append("ID inválido")
    if source.scheme != "https" or source.hostname != "dadosabertos.camara.leg.br":
        issues.append("Fonte não permitida")
    if len(str(item.get("summary", "")).strip()) < 65:
        issues.append("Ementa insuficiente")
    if not item.get("stage_date") or not item.get("stage"):
        issues.append("Sem tramitação verificável")
    if not item.get("topics"):
        issues.append("Fora das editorias")
    if any(term in (item.get("summary", "") + item.get("title", "")).casefold() for term in ELECTORAL_APPEALS):
        issues.append("Apelo eleitoral")
    return issues


def eligible(item, state, now):
    if validate_candidate(item):
        return False
    for other in state.get("pending", []) + state.get("published", []):
        if other.get("id") == item["id"] and other.get("version") == item["version"]:
            return False
        if other.get("summary_hash") and other["summary_hash"] == item["summary_hash"]:
            return False
    for old in state.get("published", []):
        if old.get("id") != item["id"]:
            continue
        try:
            last = datetime.fromisoformat(old["published_at"].replace("Z", "+00:00")).astimezone(TZ)
        except (KeyError, ValueError):
            return False
        if now - last < timedelta(days=14):
            return False
    return True


def score(item, now, topic_counts):
    try:
        days = max(0, (now.date() - datetime.fromisoformat(item["stage_date"]).date()).days)
    except (KeyError, ValueError):
        days = 365
    freshness = max(0, 30 - days * 3)
    diversity = max(0, 25 - min((topic_counts.get(t, 0) for t in item["topics"]), default=10) * 5)
    specificity = min(15, len(item["summary"]) // 45)
    return min(100, freshness + diversity + 30 + specificity)


def choose(items, state, now, maximum=3):
    counts = {}
    for old in state.get("published", []) + state.get("pending", []):
        for topic in old.get("topics", []):
            counts[topic] = counts.get(topic, 0) + 1
    candidates = [dict(x) for x in items if eligible(x, state, now)]
    for item in candidates:
        item["editorial_score"] = score(item, now, counts)
    return sorted(
        (x for x in candidates if x["editorial_score"] >= 55),
        key=lambda x: (-x["editorial_score"], x["id"]),
    )[:maximum]


def daily_limit(state):
    samples = [m for m in state.get("metrics", []) if m.get("reach", 0) >= 20]
    if len(samples) < 20:
        return 2
    rate = sum((x.get("shares", 0) + x.get("saves", 0)) / x["reach"] for x in samples) / len(samples)
    if rate >= .06 and len(samples) >= 40:
        return 3
    if rate < .01:
        return 1
    return 2


def preferred_hours(state):
    """Seleciona até 3 janelas com espaçamento mínimo de 4h, sem picos artificiais."""
    by_hour = {}
    for metric in state.get("metrics", []):
        hour = metric.get("hour")
        if metric.get("reach", 0) >= 20 and type(hour) is int and 8 <= hour <= 22:
            by_hour.setdefault(hour, []).append(
                (metric.get("shares", 0) + metric.get("saves", 0)) / metric["reach"]
            )
    target = 3 if daily_limit(state) >= 3 else 2
    baseline = [9, 14, 19] if target == 3 else [9, 19]
    reliable = sorted(
        ((sum(v) / len(v), hour) for hour, v in by_hour.items() if len(v) >= 5),
        key=lambda entry: (-entry[0], entry[1])
    )
    if len(reliable) < 2:
        return baseline
    chosen = []
    for hour in [h for _, h in reliable] + baseline + list(range(8, 23)):
        if hour not in chosen and all(abs(hour - other) >= 4 for other in chosen):
            chosen.append(hour)
        if len(chosen) == target:
            break
    return sorted(chosen)


def scan_camara(now, fetcher=None):
    if fetcher is None:
        import requests
        session = requests.Session()
        session.headers.update({"Accept": "application/json", "User-Agent": "FatoVia-Editorial/0.1"})
        def fetcher(url, params=None):
            response = session.get(url, params=params, timeout=20)
            response.raise_for_status()
            return response.json()
    root = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"
    since = (now - timedelta(days=5)).date().isoformat()
    records = fetcher(root, {"dataApresentacaoInicio": since, "ordem": "DESC", "ordenarPor": "id", "itens": 35}).get("dados", [])
    found = []
    for record in records:
        if not isinstance(record, dict) or not record.get("id") or not classify(record.get("ementa", "")):
            continue
        try:
            history = fetcher(f'{root}/{record["id"]}/tramitacoes', {"ordem": "DESC", "ordenarPor": "dataHora", "itens": 1}).get("dados", [])
            if history:
                item = from_camara(record, history[0])
                if not validate_candidate(item):
                    found.append(item)
        except Exception:
            # Fonte incompleta: não inventar, não publicar.
            continue
    return found


def rollup_report(state, now, found, staged):
    return {
        "timestamp": now.isoformat(),
        "found": found,
        "staged": staged,
        "already_published": len(state.get("published", [])),
        "pending": len(state.get("pending", [])),
        "recommended_daily_limit": daily_limit(state),
        "recommended_hours": preferred_hours(state),
        "publication": "DISABLED",
    }
