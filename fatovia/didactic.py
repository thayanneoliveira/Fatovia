"""Narrativas didáticas estritamente vinculadas a versões documentais revisadas."""
import json
from pathlib import Path
REVISION="didactic-v4"
MANIFEST=Path(__file__).resolve().parent.parent/"data/didactic_reviews.json"
KINDS=("question","proposal","mechanism","conditional","questions")

def reviewed(item):
    bundle=json.loads(MANIFEST.read_text(encoding="utf-8"))
    matches=[r for r in bundle["items"] if r["id"]==item.get("id") and r["version"]==item.get("version")]
    if not matches:
        return None
    if len(matches)!=1:
        raise ValueError("duplicate_review")
    row=matches[0]
    if bundle["revision"]!=REVISION or any(item.get(k)!=row[k] for k in ("title","summary","stage","stage_date")):
        raise ValueError("review_source_changed")
    if not row["anchors"] or not all(a in item["summary"] for a in row["anchors"]):
        raise ValueError("review_unanchored")
    cards=row["cards"]
    if len(cards)!=5 or tuple(c["kind"] for c in cards)!=KINDS:
        raise ValueError("missing_didactic_dimension")
    if any(not (8<=len(c["body"].split())<=45) or not c["headline"] or len(c["headline"])>90 or len(c["body"])>300 for c in cards):
        raise ValueError("didactic_length")
    if "se " not in cards[3]["body"].casefold() and "pode" not in cards[3]["body"].casefold():
        raise ValueError("conditional_missing")
    return row
