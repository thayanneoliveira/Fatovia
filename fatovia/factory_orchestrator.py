"""Bounded nonpublishing orchestration for the existing FatoVia pipeline.

The existing publisher remains the sole Meta writer. This module creates
content-addressed *lab tasks* for discovery -> source verification -> script
-> voice -> V5 video -> independent audit -> learning. Unknown stages fail closed.
"""
import hashlib,json
from datetime import datetime,timezone
from .audiovisual_factory import choose_validated_fixture,check_story,GateError,digest,learning_signal

STAGES=("research","script","voice","render","audit","waiting")
CODE_UNSAFE=("missing_logo","stale_source","missing_authorization","unverified_claim","wrong_account","missing_media")
SAFE_ACTIONS={
 "incomplete_speech_alignment":"rerun_independent_asr_once",
 "corrupt_video":"rerender_from_same_audited_script_and_voice",
 "render_exceeded_budget":"reduce_parallel_workers_without_reducing_resolution",
 "cover_unreadable":"regenerate_cover_from_existing_validated_frame",
 "public_asset_hash_mismatch":"reupload_same_verified_asset_once",
}
PER_STEP_ATTEMPT_LIMIT=2
COST_CEILING_BRL=0

def task_key(source,story_id,script_hash):
    return hashlib.sha256(json.dumps([source,story_id,script_hash],
          ensure_ascii=False,separators=(",",":")).encode()).hexdigest()

def safe_research_input(discovery, published_ids):
    """Discovery signals are prompts for research, NOT evidence of factual claims."""
    already=set(published_ids)
    signals=[]
    for item in discovery.get("signals",[]):
        if (item.get("id") not in already and item.get("status")=="discovery_only"
                and item.get("url","").startswith("https://")):
            signals.append({"signal_id":item["id"],"topic":item.get("topics",[]),
              "source_url":item["url"],"status":"research_required","claims":[]})
    return {"publication_authorized":False,"signals":signals,
            "reason":"Unverified public articles are not independently checked factual claims."}

def queue_fixture(candidate,script,existing):
    """Starts laboratory asset generation only for evidence-linked scripts."""
    if any(task.get("story_id")==candidate.get("id") for task in existing):
        return {"action":"skip_duplicate","publish_allowed":False}
    result=check_story(candidate,script)
    return {"action":"render_lab","story_id":candidate["id"],
            "key":task_key(candidate["source_urls"],candidate["id"],result["script_sha256"]),
            "script_sha256":result["script_sha256"],
            "source_review":"pending_independent_semantic_confirmation",
            "publish_allowed":False,"format":"reel","voice":"Santa-R-1.0",
            "visual_source":"V5-recovered"}

def correct(issues,attempts):
    """Only bounded reversible repairs, never waive a gate."""
    if not isinstance(issues,list):raise GateError("invalid issues")
    result=[]
    for issue in dict.fromkeys(issues):
        if not isinstance(issue,str):raise GateError("invalid failure")
        count=int(attempts.get(issue,0))
        if count>=PER_STEP_ATTEMPT_LIMIT:
            result.append({"reason":issue,"action":"park_for_investigation",
                           "retry":False,"retry_count":count,"publish_allowed":False})
        elif issue in SAFE_ACTIONS:
            result.append({"reason":issue,"action":SAFE_ACTIONS[issue],
                           "retry":True,"retry_count":count+1,"publish_allowed":False})
        else:
            result.append({"reason":issue,"action":"audit_block_and_investigate",
                           "retry":False,"retry_count":count,"publish_allowed":False})
    return result

def risk_gate(ledger,pending_reel,now):
    """Read-only global quota guard; no direct write action to Meta."""
    date=now.date().isoformat()
    published=[x for x in ledger.get("published",[]) if str(x.get("published_at","")).startswith(date)]
    reel_count=sum(x.get("format")=="reel" for x in published)
    if pending_reel.get("id") in {x.get("id") for x in ledger.get("published",[])}:
        return {"decision":"blocked_duplicate","publish_allowed":False}
    if reel_count>=1:
        return {"decision":"daily_reel_cap","publish_allowed":False}
    if ledger.get("publishing"):
        return {"decision":"active_transaction","publish_allowed":False}
    return {"decision":"downstream_existing_publisher_required",
            "publish_allowed":False,
            "must_use":"fatovia.publisher with full Meta identity, quota and reconciliation"}

def learn(metrics):
    results=learning_signal(metrics)
    return {**results,"strategy_auto_promotion":False,
            "next_step":"paired or cohort-matched hypotheses, source and quality gates unchanged"}

def cycle(discovery,published,fixtures,script_lookup,metrics):
    """No direct AI inference or arbitrary video generation from raw claims."""
    research=safe_research_input(discovery,[p.get("id") for p in published])
    eligible=choose_validated_fixture(fixtures,published)
    plans=[]
    if eligible:
        script=script_lookup.get(eligible.get("id"))
        if script is not None:plans.append(queue_fixture(eligible,script,[]))
    return {"mode":"lab_only","max_spend_brl":COST_CEILING_BRL,
            "research":research,"plans":plans,
            "learning":learn(metrics),
            "publisher":"existing_only","publish_allowed":False,
            "requires":"independent source, factual, aesthetic, ASR and production preflight"}
