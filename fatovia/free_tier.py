"""Check owner free-tier attestation and limited mask ambiguity without logging secrets."""
import hashlib, hmac, json, os, re
from pathlib import Path
from .narration import MODEL, VOICE

def mask_matches(row,key):
    if not isinstance(row,dict) or not isinstance(key,str):return False
    key=key.strip()
    if len(key)<20 or any(c.isspace() for c in key):return False
    fingerprint=row.get("key_suffix_sha256")
    if not isinstance(fingerprint,str) or not re.fullmatch(r"[0-9a-f]{64}",fingerprint):return False
    candidates=[fingerprint]
    if row.get("mask_alternatives_owner_confirmed") is True:
        extra=row.get("mask_alternative_sha256",[])
        if not isinstance(extra,list) or len(extra)>3 or not all(isinstance(v,str) and re.fullmatch(r"[0-9a-f]{64}",v) for v in extra):return False
        candidates+=extra
    actual=hashlib.sha256(key[-4:].encode()).hexdigest()
    return any(hmac.compare_digest(actual,v) for v in candidates)

def permitted(row,key,override=""):
    if not isinstance(row,dict) or override not in ("","true"):return False
    if not (row.get("schema")==1 and row.get("status")=="verified_free_tier" and row.get("project")=="FatoVia-TTS" and row.get("billing")=="not_configured_as_shown" and row.get("max_spend_brl")==0 and row.get("model")==MODEL and row.get("voice")==VOICE):return False
    return mask_matches(row,key)

def main():
    try: row=json.loads(Path("data/gemini_free_tier.json").read_text())
    except (OSError,ValueError):row={}
    if not isinstance(row,dict):row={}
    key=os.getenv("FATOVIA_GEMINI_API_KEY","").strip()
    override=os.getenv("FREE_OVERRIDE","")
    ok=permitted(row,key,override)
    print(json.dumps({"free_tier_verified":ok,"api_key_configured":bool(key),"mask_matches":mask_matches(row,key),"override_allows":override in ("","true"),"key_type_supported":bool(key.startswith("AQ.") or key.startswith("AIza")),"publish_allowed":False}))
    with open(os.environ["GITHUB_OUTPUT"],"a") as f:f.write("verified="+str(ok).lower()+"\n")
if __name__=="__main__":main()
