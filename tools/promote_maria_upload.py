"""Promote the owner-uploaded QuickTime container into a stream-identical MP4.

A bounded conversion, never a re-encode. Publish no content unless both encoded
audio and video packet hashes equal the owner's independently approved original.
"""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs/media/reels/FatoVia_Maria_Reel_Revisado.mov"
OUTPUT = ROOT / "docs/media/reels/FatoVia_Maria_Reel_Revisado.mp4"
POLICY = ROOT / "data/multiformat_experiment.json"
ORIGIN_SHA = "680ddcd3d0144cbc7dc332bbf04fa9a01d46449bd8cd831eea6d494f1cad8f91"
ORIGIN_SIZE = 18705744
VIDEO_HASH = "630f22001b64332a0a675491465ad8fc62d577e1759e311731e7af6e206e702b"
AUDIO_HASH = "05f5fd69e2937a07de5706b5f408da09f5b64379f530a5fcf6f78ab28b054359"
APPROVED_SHA = "f367280115d72645b712c55883c1e71838e6e6973dd7e4e1887dee46182b9170"

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def probe(path):
    p=subprocess.run(["ffprobe","-v","error","-show_streams","-show_format",
                      "-of","json",str(path)],check=True,capture_output=True,text=True)
    return json.loads(p.stdout)

def packet_hash(path,selection):
    p=subprocess.run(["ffmpeg","-v","error","-i",str(path),"-map",selection,
                      "-c","copy","-f","streamhash","-hash","SHA256","-"],
                     check=True,capture_output=True,text=True)
    return p.stdout.strip().split("SHA256=")[-1]

def check_media(path,approval):
    info=probe(path)
    streams=info["streams"]
    video=next(s for s in streams if s.get("codec_type")=="video")
    audio=next(s for s in streams if s.get("codec_type")=="audio")
    if (video["codec_name"]!="h264" or video["width"]!=1080 or video["height"]!=1920
        or video["r_frame_rate"]!="24/1" or audio["codec_name"]!="aac"
        or audio["sample_rate"]!="48000" or abs(float(info["format"]["duration"])-approval["duration_seconds"])>0.15):
        raise ValueError("Unexpected A/V metadata")
    if packet_hash(path,"0:v:0")!=VIDEO_HASH or packet_hash(path,"0:a:0")!=AUDIO_HASH:
        raise ValueError("Video or audio packet stream differs from approved original")
    return info

def run():
    p=json.loads(POLICY.read_text(encoding="utf-8"))
    approval=p["reel_editorial_override"]["owner_approval"]
    if approval["sha256"]!=APPROVED_SHA or approval["decision"]!="approved_for_publication":
        raise ValueError("Missing or changed owner approval")
    if INPUT.is_symlink() or not INPUT.is_file() or INPUT.stat().st_size!=ORIGIN_SIZE or digest(INPUT)!=ORIGIN_SHA:
        raise ValueError("Unknown or modified user upload")
    check_media(INPUT,approval)
    if not OUTPUT.exists():
        subprocess.run(["ffmpeg","-hide_banner","-v","error","-y","-i",str(INPUT),
                        "-map","0:v:0","-map","0:a:0","-c","copy","-movflags","+faststart",
                        "-f","mp4",str(OUTPUT)],check=True)
    check_media(OUTPUT,approval)
    subprocess.run(["ffmpeg","-v","error","-i",str(OUTPUT),"-f","null","-"],check=True)
    sha=digest(OUTPUT)
    size=OUTPUT.stat().st_size
    if not (1000000<size<95000000):
        raise ValueError("Unexpected remux byte size")
    p["reel_editorial_override"]["hosted_media"]={
       "status":"verified_stream_identical_remux_pending_http",
       "path":"docs/media/reels/FatoVia_Maria_Reel_Revisado.mp4",
       "sha256":sha,"bytes":size,"source_mov_sha256":ORIGIN_SHA,
       "original_approved_sha256":APPROVED_SHA,"video_stream_sha256":VIDEO_HASH,
       "audio_stream_sha256":AUDIO_HASH,"remux":"ffmpeg stream copy, no re-encode",
       "created_at":datetime.now(timezone.utc).isoformat(),
       "published_to_instagram":False
    }
    p["reel_editorial_override"]["status"]="exact_av_remux_pending_public_http_verification"
    POLICY.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"result":"STREAM_IDENTICAL_MP4_READY","sha256":sha,"bytes":size,
      "origin_sha256":ORIGIN_SHA,"source_has_same_encoded_audio_and_video":True,
      "instagram_posted":False},ensure_ascii=False))

if __name__=="__main__":
    run()
