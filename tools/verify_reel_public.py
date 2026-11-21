"""Verify public GitHub Pages bytes after deployment, no Instagram actions.

Only reports success for the exact owner-approved file over HTTPS.
"""
import hashlib
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
URL="https://thayanneoliveira.github.io/Fatovia/media/reels/FatoVia_Maria_Reel_Revisado.mp4"
LOCAL=ROOT/"docs/media/reels/FatoVia_Maria_Reel_Revisado.mp4"

def run():
    if not LOCAL.is_file():
        print("REEL_NOT_YET_UPLOADED: public-host check skipped")
        return
    approval=json.loads((ROOT/"data/multiformat_experiment.json").read_text(encoding="utf-8"))["reel_editorial_override"]["owner_approval"]
    expected=approval["sha256"]
    last_error=""
    for attempt in range(6):
        try:
            req=urllib.request.Request(URL,headers={"User-Agent":"FatoVia-ContentAudit/1.0"})
            with urllib.request.urlopen(req,timeout=35) as response:
                if response.status!=200 or "video/mp4" not in response.headers.get("Content-Type","").lower():
                    raise RuntimeError("Public origin did not return video/mp4 HTTP 200")
                h=hashlib.sha256();size=0
                while True:
                    chunk=response.read(65536)
                    if not chunk:break
                    size+=len(chunk)
                    if size>approval["bytes"]:raise RuntimeError("Public file exceeds approved size")
                    h.update(chunk)
                if size!=approval["bytes"] or h.hexdigest()!=expected:
                    raise RuntimeError("Public video does not match owner-approved SHA-256")
            print(json.dumps({"status":"PUBLIC_MP4_VERIFIED","url":URL,"sha256":expected,"bytes":size,"published_to_instagram":False}))
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
