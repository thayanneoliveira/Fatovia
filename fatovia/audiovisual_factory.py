"""FatoVia audiovisual factory contract, no publishing and no authentication.

This module is a strict bridge between existing discovery, script, V5 render,
independent audit and the EXISTING publisher. It does not invent fact verification
or authorize speculative captions. All artefacts are lab-only by default.
"""
from __future__ import annotations
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

VOICE="Santa-R-1.0"
SCENES={
    "hook":"announcement",
    "person":"character",
    "announcement":"announcement",
    "human_consequence":"hope",
    "time":"waiting",
    "investigation":"investigate",
    "action":"investigate",
    "official_source":"portal",
    "caveat":"caveat",
    "verification":"checklist",
    "discovery":"contrast",
    "reflection":"reflect",
    "brand":"brand",
}
TRUSTED={"www.gov.br","gov.br","obrasgov.sistema.gov.br","portaldatransparencia.gov.br",
         "www.ibge.gov.br","ibge.gov.br"}
ALLOWED={
 "lab_only_no_publish","prepared_pending_independent_review",
 "rejected","audited_lab_only"
}
LOGO="df41d13bb11db469d2850c69c0ece41eeb7e33a262e7622b59afb21ef81c7ce6"
HEX64=re.compile(r"[0-9a-f]{64}\Z")
NOISE=re.compile(r"\b(corrup[cç][aã]o|desvio|fraude|roubo)\b",re.I)

class GateError(ValueError):pass

def canonical(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf8")

def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()

def text(value):
    return isinstance(value,str) and bool(value.strip())

def official_url(url):
    try:
        u=urlparse(url)
        return u.scheme=="https" and u.hostname in TRUSTED and not u.username and not u.password
    except (TypeError,ValueError,AttributeError):return False

def check_story(story,script):
    """Strict schema checks, NOT a substitute for human-level fact checking."""
    if not isinstance(story,dict) or not isinstance(script,list):raise GateError("invalid objects")
    if story.get("status") not in ALLOWED or story.get("status")!="lab_only_no_publish":raise GateError("not a lab input")
    if story.get("voice")!=VOICE or story.get("visual_revision") not in ("V5-lab","V5"):raise GateError("unapproved artistic profile")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{7,90}",str(story.get("id",""))):raise GateError("invalid story identity")
    if not 7<=len(script)<=100:raise GateError("invalid script length")
    scenes=story.get("beats")
    if not isinstance(scenes,list) or len(scenes)!=len(script):raise GateError("missing scene coverage")
    urls=story.get("source_urls")
    if not isinstance(urls,list) or not urls or not all(official_url(x) for x in urls):raise GateError("sources must be official HTTPS")
    claims=story.get("claims",[])
    if not isinstance(claims,list) or len({x.get("id") for x in claims})!=len(claims):raise GateError("bad claim IDs")
    ids={x["id"] for x in claims}
    for c in claims:
        if not text(c.get("id")) or not official_url(c.get("source")) or c["source"] not in urls:raise GateError("unmapped claim")
    for i,(b,p) in enumerate(zip(scenes,script)):
        if b.get("phrase_index")!=i or b.get("role") not in SCENES:raise GateError("scene ordering or unknown action")
        if not text(p.get("caption")) or len(p["caption"])>300 or not text(p.get("spoken",p["caption"])):raise GateError("bad speech")
        if "exemplo fictício" in p["caption"].casefold():raise GateError("intrusive spoken disclaimer")
        if b.get("role")=="official_source" and not b.get("claim_ids"):raise GateError("unmapped factual narration")
        if not isinstance(b.get("claim_ids",[]),list) or not set(b.get("claim_ids",[]))<=ids:raise GateError("unknown claim")
        if b.get("role")=="brand" and i<len(script)-2:raise GateError("brand appears before ending")
    if scenes[-1]["role"]!="brand":raise GateError("missing branded ending")
    if not story.get("person"):raise GateError("missing relatable person")
    # Word blacklists are not truth judges: this is a safe default for high-risk assertions.
    if any(NOISE.search(p["caption"]) for p in script) and not story.get("special_claim_review"):
        raise GateError("high-risk allegation must have independent specialist review")
    return {"status":"structural_pass_fact_review_pending","script_sha256":digest(script),
            "story_sha256":digest(story),"beats":len(scenes),
            "roles":[b["role"] for b in scenes],"sources":urls}

def plan(story,script,voice_manifest):
    checked=check_story(story,script)
    if voice_manifest.get("profile")!=VOICE or voice_manifest.get("phrases")!=len(script):
        raise GateError("Santa R profile or phrase count mismatch")
    blocks=voice_manifest.get("blocks")
    if not isinstance(blocks,list) or not blocks:raise GateError("no source TTS timeline")
    cursor=0;prev=-1.;phrases=[]
    for block in blocks:
        a,b=block["phrase_first"]-1,block["phrase_last"]
        start,end=float(block["start"]),float(block["end"])
        if a!=cursor or b>len(script) or b<=a or start<prev or end<=start:
            raise GateError("broken synthesis timeline")
        chunk=script[a:b];weights=[max(7,len(x.get("spoken",x["caption"]))) for x in chunk]
        pos=start
        for j,(piece,weight) in enumerate(zip(chunk,weights)):
            nextpos=end if j==len(chunk)-1 else pos+(end-pos)*weight/sum(weights[j:])
            phrases.append({"id":j+a,"start":pos,"end":nextpos,"caption":piece["caption"],
                            "scene":SCENES[story["beats"][j+a]["role"]],
                            "role":story["beats"][j+a]["role"],
                            "claim_ids":story["beats"][j+a].get("claim_ids",[])})
            pos=nextpos
        cursor=b;prev=end
    if cursor!=len(script):raise GateError("incomplete narration")
    return {"status":"lab_only","publish_allowed":False,"story_id":story["id"],"story_sha256":checked["story_sha256"],
            "script_sha256":checked["script_sha256"],"voice":VOICE,"voice_manifest_sha256":digest(voice_manifest),
            "seconds":float(voice_manifest["duration"]),"scenes":phrases,
            "caption_timing":"estimated_inside_verified_tts_blocks_requires_asr",
            "logo_sha256":LOGO,"sources":checked["sources"]}

def independent_gate(plan_obj,technical,factual,visual,asr):
    """Independent sign-off object intentionally fails closed on missing assessments."""
    findings=[]
    if plan_obj.get("publish_allowed") is not False:findings.append("lab_plan_unexpectedly_permissive")
    if not technical.get("valid"):findings.append("technical_not_passed")
    if not factual.get("reviewed_by_independent_agent") or factual.get("uncorroborated_claims"):
        findings.append("independent_fact_review_pending")
    if not visual.get("reviewed_by_independent_agent") or visual.get("artistic_equivalence") not in ("equivalent","superior"):
        findings.append("v5_artistic_equivalence_unproven")
    if not asr.get("independent_recognition") or not asr.get("word_level_alignment_validated"):
        findings.append("word_level_subtitles_unverified")
    if technical.get("logo_sha256")!=LOGO:findings.append("missing_owner_logo")
    if technical.get("fps")!=24 or technical.get("dimensions")!=[1080,1920]:
        findings.append("incorrect_video_technical_profile")
    return {"decision":"rejected" if findings else "independent_review_passed_only",
            "publish_allowed":False,"findings":findings,"input_media_sha256":technical.get("sha256"),
            "notes":"Even full independent review never bypasses existing publisher policies."}

def learning_signal(samples, minimum=20):
    """Descriptive rates only, never causation or auto-promotion from tiny samples."""
    if not isinstance(samples,list):raise GateError("bad metrics")
    normalized=[]
    for row in samples:
        reach=row.get("reach");shares=row.get("shares");saves=row.get("saves")
        if any(not isinstance(v,int) or isinstance(v,bool) or v<0 for v in (reach,shares,saves)):
            continue
        if reach==0:continue
        normalized.append({"id":row.get("id"),"shares_per_reach":shares/reach,"saves_per_reach":saves/reach,
                           "source":row.get("source","unverified"),"reach":reach})
    return {"samples":len(normalized),"eligible_for_strategy_change":len(normalized)>=minimum,
            "status":"hypothesis_only_insufficient_sample" if len(normalized)<minimum else "descriptive_comparison_possible",
            "observations":normalized,"causality_claimed":False}

def choose_validated_fixture(candidates,published):
    """No content generation or invented facts: select only independently sourced fixture candidates."""
    already={x.get("id") for x in published}
    eligible=[x for x in candidates if x.get("id") not in already and x.get("status")=="lab_only_no_publish"
              and all(official_url(u) for u in x.get("source_urls",[]))]
    if not eligible:return None
    return sorted(eligible,key=lambda x:(-int(x.get("source_quality_score",0)),str(x.get("id"))))[0]
