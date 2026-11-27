"""Owner evidence for free tier, checked against the configured secret without logging it."""
import hashlib, hmac, json, os, re
from pathlib import Path
from .narration import MODEL, VOICE
def permitted(row,key,override=""):
    if not isinstance(row,dict) or not isinstance(key,str) or override not in ("","true"):return False
    key=key.strip()
    if not (row.get("schema")==1 and row.get("status")=="verified_free_tier" and row.get("project")=="FatoVia-TTS" and row.get("billing")=="not_configured_as_shown" and row.get("max_spend_brl")==0 and row.get("model")==MODEL and row.get("voice")==VOICE and len(key)>=20):return False
    fingerprint=row.get("key_suffix_sha256")
    if not isinstance(fingerprint,str) or not re.fullmatch(r"[0-9a-f]{64}",fingerprint):return False
    return hmac.compare_digest(hashlib.sha256(key[-4:].encode()).hexdigest(),fingerprint)
def main():
    try: row=json.loads(Path("data/gemini_free_tier.json").read_text())
    except (OSError,ValueError):row={}
    key=os.getenv("FATOVIA_GEMINI_API_KEY","").strip()
    override=os.getenv("FREE_OVERRIDE","")
    ok=permitted(row,key,override)
    identity_matches=bool(len(key)>=20 and isinstance(row.get("key_suffix_sha256"),str) and hmac.compare_digest(hashlib.sha256(key[-4:].encode()).hexdigest(),row["key_suffix_sha256"]))
    policy_valid=permitted(row,key,"") if identity_matches else False
    print(json.dumps({"key_suffix_matches":identity_matches,"override_allows":override in ("","true"),"attestation_valid_for_key":policy_valid,"reason":"verified" if ok else "override_veto" if override not in ("","true") else "key_suffix_mismatch_or_missing" if not identity_matches else "attestation_invalid"}))
    with open(os.environ["GITHUB_OUTPUT"],"a") as f:f.write("verified="+str(ok).lower()+"\n")
    print(json.dumps({"free_tier_verified":ok,"api_key_configured":bool(os.getenv("FATOVIA_GEMINI_API_KEY")),"publish_allowed":False}))
if __name__=="__main__":main()
