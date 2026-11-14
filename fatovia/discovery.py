"""Discovery-only radar: public RSS, IBGE news, Explore annotations.
No feed content is automatically authorized as a publishable factual claim.
"""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
from urllib.parse import urlsplit, urlunsplit
import re
import xml.etree.ElementTree as ET
import requests
from .engine import classify

FEEDS = {
    "agencia_brasil": ("https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml", "agenciabrasil.ebc.com.br"),
    "senado": ("https://www12.senado.leg.br/noticias/feed/todasnoticias/RSS", "www12.senado.leg.br"),
}
IBGE = "https://servicodados.ibge.gov.br/api/v3/noticias/"
MAX_BYTES = 2_000_000


def get(url, params=None):
    with requests.get(url, params=params, timeout=(8, 15), stream=True,
                      allow_redirects=False, headers={"User-Agent": "FatoVia-Radar/1.0"}) as r:
        if r.status_code != 200:
            raise ValueError("source_http_" + str(r.status_code))
        body = bytearray()
        for chunk in r.iter_content(32768):
            body.extend(chunk)
            if len(body) > MAX_BYTES:
                raise ValueError("source_too_large")
        return bytes(body)


def canonical(url, host):
    p = urlsplit(str(url))
    if p.scheme != "https" or p.netloc != host or not p.path or p.path == "/":
        return None
    return urlunsplit(("https", host, p.path.rstrip("/"), "", ""))


def clean(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()[:300]


def date_rss(text):
    try:
        d = parsedate_to_datetime(text)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def make(source, title, url, date, now):
    title = clean(title)
    if not title or not url or not date or not now-timedelta(days=7) <= date <= now:
        return None
    topics = classify(title)
    if not topics:
        return None
    return {"id": sha256(url.encode()).hexdigest()[:20], "source": source,
            "title": title, "url": url, "published_at": date.isoformat(),
            "topics": topics, "status": "discovery_only"}


def parse_rss(body, source, host, now):
    if re.search(br"<!\s*(DOCTYPE|ENTITY)", body, re.I):
        raise ValueError("unsafe_xml")
    root = ET.fromstring(body)
    rows = []
    for node in root.findall(".//item")[:60]:
        row = make(source, node.findtext("title"), canonical(node.findtext("link"), host),
                   date_rss(node.findtext("pubDate")), now)
        if row:
            rows.append(row)
    return rows


def parse_ibge(body, now):
    import json
    from zoneinfo import ZoneInfo
    rows = []
    for item in json.loads(body).get("items", [])[:60]:
        try:
            dt = datetime.strptime(item["data_publicacao"], "%d/%m/%Y %H:%M:%S").replace(
                tzinfo=ZoneInfo("America/Sao_Paulo"))
            row = make("ibge", item.get("titulo"), canonical(item.get("link"), "agenciadenoticias.ibge.gov.br"), dt, now)
            if row:
                rows.append(row)
        except (ValueError, KeyError, TypeError):
            continue
    return rows


def collect(now, getter=get):
    rows, status = [], {}
    for source, (url, host) in FEEDS.items():
        try:
            found = parse_rss(getter(url), source, host, now)
            rows += found
            status[source] = {"status": "ok", "eligible_signals": len(found)}
        except Exception as exc:
            status[source] = {"status": "unavailable", "error_type": type(exc).__name__}
    try:
        found = parse_ibge(getter(IBGE, {"qtd": 40, "destaque": "n"}), now)
        rows += found
        status["ibge"] = {"status": "ok", "eligible_signals": len(found)}
    except Exception as exc:
        status["ibge"] = {"status": "unavailable", "error_type": type(exc).__name__}
    unique = {x["id"]: x for x in rows}
    return list(unique.values()), status


def summarize(rows, state, now):
    groups = {}
    for row in rows:
        for topic in row["topics"]:
            g = groups.setdefault(topic, {"sources": set(), "documents": set(), "explore": set()})
            g["sources"].add(row["source"])
            g["documents"].add(row["id"])
    for signal in state.get("explore_signals", []):
        try:
            dt = datetime.fromisoformat(signal["observed_at"])
            if signal.get("source") != "manual_explore" or not now-timedelta(days=7) <= dt <= now:
                continue
            url = canonical(signal["url"], "www.instagram.com")
            if not url or not re.fullmatch(r"https://www.instagram.com/(?:p|reel)/[A-Za-z0-9_-]{4,40}", url):
                continue
            g = groups.setdefault(signal["topic"], {"sources": set(), "documents": set(), "explore": set()})
            g["explore"].add(url)
        except (ValueError, KeyError, TypeError):
            continue
    result = [{"topic": t, "source_count": len(g["sources"]), "document_count": len(g["documents"]),
               "explore_links": len(g["explore"]), "sources": sorted(g["sources"]),
               "status": "research_required"} for t,g in groups.items()]
    return sorted(result, key=lambda g: (-g["source_count"], -g["explore_links"], -g["document_count"], g["topic"]))


def run(state, now):
    rows, status = collect(now)
    return {"generated_at": now.isoformat(), "sources": status, "signals": rows,
            "topic_groups": summarize(rows, state, now), "publication_authorized": False,
            "note": "Topic co-occurrence is not corroboration of an individual claim or proof of virality."}
