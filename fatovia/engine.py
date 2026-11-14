"""Radar editorial documental e seleção determinística. Não recomenda candidaturas."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from .memory import duplicate
from .evidence import source_ok

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
    if source.scheme != "https" or source.hostname != "dadosabertos.camara.leg.br" or not source_ok(item):
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
        if duplicate(item, other):
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
    candidates = [dict(x) for x in items if eligible(x, state, now) and fresh_stage(x, now)]
    for item in candidates:
        item["editorial_score"] = score(item, now, counts)
    # Explorar e apenas um sinal de descoberta, nunca evidencia factual.
    # Nao altera o limiar de elegibilidade; desempata pautas documentadas.
    signals = {}
    for signal in state.get("explore_signals", []):
        if signal.get("source") != "manual_explore":
            continue
        topic = signal.get("topic")
        if topic not in TOPICS:
            continue
        try:
            dt = datetime.fromisoformat(signal["observed_at"])
            if not now - timedelta(days=7) <= dt <= now:
                continue
            url = urlparse(signal["url"])
            if (url.scheme != "https" or url.netloc != "www.instagram.com"
                    or not re.fullmatch(r"/(?:p|reel)/[A-Za-z0-9_-]{4,40}/?", url.path)):
                continue
            signals.setdefault(topic, set()).add(url.path.rstrip("/"))
        except (KeyError, TypeError, ValueError):
            continue
    for item in candidates:
        item["explore_signal_count"] = min(3, sum(len(signals.get(t, set())) for t in item["topics"]))
    groups = state.get("discovery_topic_groups", [])
    trend = {g["topic"]: min(3, g.get("source_count", 0)) for g in groups if g.get("topic") in TOPICS}
    for item in candidates:
        item["discovery_source_count"] = max((trend.get(t,0) for t in item["topics"]),default=0)
    ranked = sorted(
        (x for x in candidates if x["editorial_score"] >= 55),
        key=lambda x: (-x["editorial_score"], -x["explore_signal_count"], -x["discovery_source_count"], x["id"]),
    )
    selected = []
    for item in ranked:
        if any(duplicate(item, other) for other in selected):
            continue
        if len(selected) >= maximum:
            break
        selected.append(item)
    return selected


# Fixed experimental cadence; no engagement-driven changes without validated review.
EXPERIMENT_HOURS = (9, 13, 17, 21)
MIN_PUBLICATION_GAP_HOURS = 3


def daily_limit(state):
    return len(EXPERIMENT_HOURS)


def preferred_hours(state):
    return list(EXPERIMENT_HOURS)


def fresh_stage(item, now):
    try:
        return 0 <= (now.date() - datetime.fromisoformat(item["stage_date"]).date()).days <= 14
    except (ValueError, KeyError, TypeError):
        return False


def scan_camara(now, fetcher=None, diagnostics=None):
    if fetcher is None:
        import requests
        session = requests.Session()
        session.headers.update({"Accept": "application/json", "User-Agent": "FatoVia-Editorial/0.1"})
        def fetcher(url, params=None):
            response = session.get(url, params=params, timeout=20)
            response.raise_for_status()
            return response.json()
    root = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"
    # Use a longer discovery window, but never relax the gate for recent tramitation.
    since = (now - timedelta(days=14)).date().isoformat()
    records = fetcher(root, {"dataApresentacaoInicio": since, "ordem": "DESC", "ordenarPor": "id", "itens": 100}).get("dados", [])
    if not isinstance(records, list):
        raise ValueError("Invalid source response")
    counts = {"records":len(records),"topic_matches":0,"history_missing":0,"history_errors":0,"invalid":0,"stale":0,"verified":0}
    found = []
    for record in records:
        if not isinstance(record, dict) or not record.get("id") or not classify(record.get("ementa", "")):
            continue
        counts["topic_matches"] += 1
        # Bound remote history calls per scan.
        if counts["topic_matches"] > 25:
            break
        try:
            history = fetcher(f'{root}/{record["id"]}/tramitacoes', {"ordem": "DESC", "ordenarPor": "dataHora", "itens": 1}).get("dados", [])
            if not history:
                counts["history_missing"] += 1
                continue
            item = from_camara(record, history[0])
            if validate_candidate(item):
                counts["invalid"] += 1
            elif not fresh_stage(item, now):
                counts["stale"] += 1
            else:
                found.append(item)
                counts["verified"] += 1
        except Exception:
            counts["history_errors"] += 1
    if diagnostics is not None:
        diagnostics.update(counts)
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
