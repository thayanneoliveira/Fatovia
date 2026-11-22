"""Verify exact public MP4 over HTTPS after Pages deploy, no Meta publication."""
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/"docs/media/reels/FatoVia_Maria_Reel_Revisado.mp4"
URL="https://thayanneoliveira.github.io/Fatovia/media/reels/FatoVia_Maria_Reel_Revisado.mp4"

def run():
    if not LOCAL.is_file():
        print("REEL_NOT_YET_UPLOADED: public HTTP check skipped")
        return
    cfg=json.loads((ROOT/"data/multiformat_experiment.json").read_text(encoding="utf-8"))["reel_editorial_override"]
    approval=cfg["owner_approval"]
    hosted=cfg.get("hosted_media")
    if hosted and hosted.get("original_approved_sha256")==approval["sha256"]:
        expected=hosted["sha256"];nexpected=hosted["bytes"]
    else:
        expected=approval["sha256"];nexpected=approval["bytes"]
    last_error=""
    for attempt in range(6):
        try:
            req=urllib.request.Request(URL,headers={"User-Agent":"FatoVia-ContentAudit/1.0"})
            with urllib.request.urlopen(req,timeout=35) as response:
                if response.status!=200 or "video/mp4" not in response.headers.get("Content-Type","").lower():
                    raise RuntimeError("Public origin did not return MP4 HTTP 200")
                h=hashlib.sha256();n=0
                while True:
                    block=response.read(65536)
                    if not block:break
                    n+=len(block)
                    if n>nexpected:raise RuntimeError("Public file larger than expected")
                    h.update(block)
                if n!=nexpected or h.hexdigest()!=expected:
                    raise RuntimeError("Public MP4 does not match approved-source remux SHA256")
            print(json.dumps({"status":"PUBLIC_MP4_VERIFIED","url":URL,
                              "sha256":expected,"bytes":n,"published_to_instagram":False}))
            return
        except Exception as exc:
            last_error=str(exc)
            if attempt<5:time.sleep(10)
    raise RuntimeError("Public MP4 not verified: "+last_error)

if __name__=="__main__":
    try:run()
    except Exception as exc:
        print(type(exc).__name__+": "+str(exc),file=sys.stderr)
        raise SystemExit(1)
