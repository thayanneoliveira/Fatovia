"""Validate the user-approved Maria MP4 before publishing it as a Pages asset.

Fail closed on wrong media, preserving the carousel site when no Reel exists yet.
Does not post to Meta, expose a token, or modify the approved video.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "data/multiformat_experiment.json"
VIDEO = ROOT / "docs/media/reels/FatoVia_Maria_Reel_Revisado.mp4"

def run():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    approval = policy["reel_editorial_override"]["owner_approval"]
    if VIDEO.name != approval["filename"] or approval["decision"] != "approved_for_publication":
        raise RuntimeError("Approval does not match the proposed media path")
    if not VIDEO.exists():
        print("MARIA_REEL_ABSENT: no approved MP4 in Pages source; existing carousels unaffected")
        return "not_uploaded"
    if VIDEO.is_symlink() or not VIDEO.is_file():
        raise RuntimeError("Untrusted media path")
    expected = approval["sha256"]
    size = VIDEO.stat().st_size
    digest = hashlib.file_digest(VIDEO.open("rb"), "sha256").hexdigest()
    if size != approval["bytes"] or digest != expected:
        raise RuntimeError("Rejected: file does not match approved bytes")
    if VIDEO.read_bytes()[:4] == b"":
        raise RuntimeError("Invalid MP4")
    info = json.loads(subprocess.run([
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(VIDEO)
    ], check=True, capture_output=True, text=True).stdout)
    streams = info["streams"]
    v = next(s for s in streams if s["codec_type"] == "video")
    a = next(s for s in streams if s["codec_type"] == "audio")
    checks = [
        v["codec_name"] == approval["video_codec"],
        (v["width"], v["height"]) == tuple(approval["dimensions"]),
        v["r_frame_rate"] == "24/1",
        a["codec_name"] == approval["audio_codec"],
        int(a["sample_rate"]) == approval["audio_sample_rate"],
        abs(float(info["format"]["duration"]) - approval["duration_seconds"]) < 0.15,
    ]
    if not all(checks):
        raise RuntimeError("Rejected: metadata does not match owner-approved media")
    print(json.dumps({
        "status": "APPROVED_SOURCE_MATCH",
        "file": VIDEO.relative_to(ROOT).as_posix(),
        "sha256": digest,
        "bytes": size,
        "note": "Pages upload verification only; not a public HTTP or Instagram publication confirmation",
    }, ensure_ascii=False))
    return "ready"

if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        raise SystemExit(1)
