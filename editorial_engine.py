"""Experimental educational script contract. No publisher, network or model calls."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parent
POLICY=json.loads((ROOT/"protocol.json").read_text(encoding="utf-8"))
STAGES=POLICY["stages"]
RUBRIC=tuple(POLICY["rubric"])

def nonempty(v):
    return isinstance(v,str) and bool(v.strip())

def fingerprint(obj):
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def valid_url(v):
    if not nonempty(v): return False
    u=urlparse(v)
    return u.scheme=="https" and bool(u.hostname) and not u.username and not u.password

def audit(draft, review=None):
    """Checks structure, not truth or semantic quality. Never authorizes publishing."""
    issues=[]
    if not isinstance(draft,dict): return {"status":"revise","issues":["not_object"],"publish_allowed":False}
    for k in ("id","central_question","audience_impact"):
        if not nonempty(draft.get(k)): issues.append("missing:"+k)
    beats=draft.get("beats")
    if not isinstance(beats,list) or any(not isinstance(b,dict) for b in beats):
        beats=[]; issues.append("invalid_beats")
    if [b.get("stage") for b in beats]!=STAGES: issues.append("missing_or_disordered_stages")
    claims=draft.get("claims")
    if not isinstance(claims,list) or any(not isinstance(c,dict) for c in claims):
        claims=[]; issues.append("invalid_claims")
    ids=[c.get("id") for c in claims if nonempty(c.get("id"))]
    if len(ids)!=len(claims) or len(set(ids))!=len(ids): issues.append("invalid_claim_ids")
    for c in claims:
        k=c.get("kind"); ident=c.get("id")
        if not nonempty(c.get("text")) or k not in ("fact","fiction","hypothesis","question"):
            issues.append("invalid_claim:"+str(ident)); continue
        if k=="fact" and (not valid_url(c.get("source_url")) or not nonempty(c.get("source_excerpt")) or not nonempty(c.get("source_date"))):
            issues.append("fact_without_evidence:"+str(ident))
        if k in ("fiction","hypothesis") and not nonempty(c.get("disclosure")):
            issues.append("undisclosed_example:"+str(ident))
    used=set()
    for b in beats:
        s=b.get("stage")
        if not nonempty(b.get("narration")): issues.append("empty_narration:"+str(s))
        refs=b.get("claim_ids")
        if not isinstance(refs,list) or any(not isinstance(x,str) or x not in ids for x in refs):
            issues.append("unmapped_claim:"+str(s))
        else: used.update(refs)
        if s in ("mechanism","impact","responsibility","solutions") and not refs:
            issues.append("missing_claim_mapping:"+s)
    if set(ids)!=used: issues.append("orphan_claims")
    action=draft.get("action") or {}
    if not isinstance(action,dict) or any(not nonempty(action.get(k)) for k in ("responsible","question","indicator","how")) or not valid_url(action.get("url")):
        issues.append("non_verifiable_action")
    if not nonempty(draft.get("tradeoff")): issues.append("missing_tradeoff")
    if not nonempty(draft.get("final_question")) or not draft["final_question"].endswith("?"): issues.append("missing_open_question")
    h=fingerprint(draft)
    status="revise" if issues else "needs_semantic_review"
    if not issues and isinstance(review,dict):
        scores=review.get("scores",{})
        if review.get("draft_sha256")!=h: issues.append("stale_review")
        elif review.get("kind")!="independent_editorial_review" or not nonempty(review.get("reviewer")) or not isinstance(scores,dict) or set(scores)!=set(RUBRIC) or any(type(v)!=int or not 1<=v<=5 for v in scores.values()): issues.append("invalid_review")
        elif not all(review.get(k) is True for k in ("facts_verified","neutrality_verified","fiction_disclosed","action_verified")): issues.append("semantic_gate_incomplete")
        elif min(scores.values())<4: issues.append("rubric_below_threshold")
        else: status="editorial_candidate_only"
        if issues: status="revise"
    return {"status":status,"issues":issues,"draft_sha256":h,"publish_allowed":False,"limitations":"Structural checks and recorded review only; no autonomous factual/semantic verification."}

def prompt(topic):
    return ("FatoVia | Roteirista experimental. Tema: "+topic+"\n"
       +"Uma pergunta central, conhecimento prévio zero. Mecanismo antes do termo. "
       +"Conduza a história sem induzir posição política; não confunda hipótese com fato. "
       +"Entregue JSON com id, central_question, audience_impact, beats (stage, narration, claim_ids), "
       +"claims (id, kind, text; para fact: source_url, source_excerpt, source_date; para fiction/hypothesis: disclosure), "
       +"action (responsible, question, indicator, how, url), tradeoff, final_question. "
       +"Não invente evidências, deixe lacunas explícitas. Não publique.\n"
       +json.dumps(POLICY,ensure_ascii=False,indent=2))

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--topic");p.add_argument("--draft",type=Path);p.add_argument("--review",type=Path)
    a=p.parse_args()
    if a.topic: print(prompt(a.topic))
    elif a.draft: print(json.dumps(audit(json.loads(a.draft.read_text()),json.loads(a.review.read_text()) if a.review else None),ensure_ascii=False,indent=2))
    else: p.error("Provide --topic or --draft")
