"""Reject any Pages MP4 that isn't exactly the owner's approved source or a
verified stream-identical rewrap of it. No Instagram actions.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from promote_maria_upload import INPUT, ORIGIN_SHA, APPROVED_SHA, check_media, digest

ROOT=Path(__file__).resolve().parents[1]
POLICY=ROOT/"data/multiformat_experiment.json"
VIDEO=ROOT/"docs/media/reels/FatoVia_Maria_Reel_Revisado.mp4"

def run():
    p=json.loads(POLICY.read_text(encoding="utf-8"))
    approval=p["reel_editorial_override"]["owner_approval"]
    if approval["decision"]!="approved_for_publication" or approval["sha256"]!=APPROVED_SHA or VIDEO.name!=approval["filename"]:
        raise RuntimeError("Owner approval mismatch")
    if not VIDEO.exists():
        print("MARIA_REEL_ABSENT: carrossel Pages site unaffected")
        return "not_uploaded"
    if VIDEO.is_symlink() or not VIDEO.is_file():
        raise RuntimeError("Untrusted video path")
    actual=digest(VIDEO)
    size=VIDEO.stat().st_size
    if actual==approval["sha256"] and size==approval["bytes"]:
        check_media(VIDEO,approval)
        state="APPROVED_ORIGINAL_BYTES"
    else:
        hosted=p["reel_editorial_override"]["hosted_media"]
        checks=(
            hosted["status"] in ("verified_stream_identical_remux_pending_http","verified_stream_identical_remux_hosted"),
            hosted["path"]==VIDEO.relative_to(ROOT).as_posix(),
            hosted["sha256"]==actual and hosted["bytes"]==size,
            hosted["source_mov_sha256"]==ORIGIN_SHA,
            hosted["original_approved_sha256"]==APPROVED_SHA,
            INPUT.is_file() and not INPUT.is_symlink() and digest(INPUT)==ORIGIN_SHA,
        )
        if not all(checks):raise RuntimeError("Remux provenance or exact bytes mismatch")
        check_media(INPUT,approval)
        check_media(VIDEO,approval)
        state="STREAM_IDENTICAL_MP4_REWRAP"
    print(json.dumps({"status":state,"sha256":actual,"bytes":size,
      "path":VIDEO.relative_to(ROOT).as_posix(),
      "note":"Pages pre-deployment verification; Instagram publishing is separate"},ensure_ascii=False))
    return "ready"

if __name__=="__main__":
    try:run()
    except Exception as exc:
        print(type(exc).__name__+": "+str(exc),file=sys.stderr)
        raise SystemExit(1)
