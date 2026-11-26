"""Isolated Algenib TTS adapter. No publish operations or automatic paid fallback."""
import argparse
import base64
import hashlib
import io
import json
import os
import struct
import tempfile
import wave
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

MODEL = "gemini-3.8-flash-tts"
VOICE = "Algenib"
URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
STYLE = ("Native Brazilian Portuguese. Natural, spontaneous and conversational delivery. "
         "Genuine curiosity, subtle emotional variations, natural breathing, dynamic pacing "
         "and short meaningful pauses. Avoid robotic cadence, exaggerated drama, advertising "
         "tone and news anchor delivery. Authentic Brazilian male content creator.")
MAX_SCRIPT = 4000
MAX_RESPONSE = 20_000_000

class NarrationError(RuntimeError):
    pass

def payload(script, style=STYLE):
    if not isinstance(script, str) or not script.strip() or len(script)>MAX_SCRIPT:
        raise NarrationError("invalid script")
    if not isinstance(style, str) or not style.strip() or len(style)>2000:
        raise NarrationError("invalid style")
    return {"model":MODEL, "input":[{"type":"user_input","content":[
        {"type":"text","text":script,"annotations":[{"type":"speech_metadata","style":style}]}]}],
        "response_format":{"type":"audio"},
        "generation_config":{"speech_config":[{"voice":VOICE}]}}

def validate_wav(raw):
    try:
        with wave.open(io.BytesIO(raw),"rb") as w:
            rate, width, channels, n = w.getframerate(),w.getsampwidth(),w.getnchannels(),w.getnframes()
            if rate!=24000 or width!=2 or channels!=1 or not 0.5<=n/rate<=180:
                raise NarrationError("unexpected audio format or duration")
            frames=w.readframes(n)
            if len(frames)!=n*2:
                raise NarrationError("truncated audio")
            samples=struct.iter_unpack("<h",frames)
            peak=max((abs(v[0]) for v in samples),default=0)
            if peak<100:
                raise NarrationError("silent audio")
            return {"duration_seconds":round(n/rate,3),"sample_rate":rate,"peak":peak}
    except (wave.Error,EOFError,ZeroDivisionError,struct.error):
        raise NarrationError("invalid WAV") from None

def extract_wav(result):
    try:
        if result.get("status") not in (None,"completed"):
            raise NarrationError("interaction not completed")
        parts=[part for step in result["steps"] if step.get("type")=="model_output"
               for part in step["content"] if part.get("type")=="audio"]
        if len(parts)!=1:
            raise NarrationError("expected exactly one audio block")
        raw=base64.b64decode(parts[0]["data"],validate=True)
        validate_wav(raw)
        return raw
    except (KeyError,TypeError,ValueError,AttributeError):
        raise NarrationError("invalid audio response") from None

def _atomic(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
        tmp=Path(f.name)
        f.write(raw)
    try:
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)

def generate(script, cache_dir, style=STYLE, *, env=None, opener=None):
    """One request maximum per invocation; no retry or fallback. Cache is private."""
    env=os.environ if env is None else env
    request=payload(script,style)
    body=json.dumps(request,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()
    cache_key=hashlib.sha256(body).hexdigest()
    path=Path(cache_dir)/(cache_key+".wav")
    seal=path.with_suffix(".json")
    if path.exists() and seal.exists():
        raw=path.read_bytes()
        meta=json.loads(seal.read_text(encoding="utf-8"))
        if meta.get("sha256")==hashlib.sha256(raw).hexdigest() and meta.get("request_sha256")==cache_key:
            validate_wav(raw)
            return path
        raise NarrationError("cache integrity mismatch")
    if env.get("FATOVIA_GEMINI_FREE_TIER_VERIFIED")!="true":
        raise NarrationError("free tier not verified; no request sent")
    key=env.get("FATOVIA_GEMINI_API_KEY","").strip()
    if not key:
        raise NarrationError("missing dedicated free-tier API key; no request sent")
    req=Request(URL,data=body,headers={"Content-Type":"application/json","x-goog-api-key":key},method="POST")
    try:
        with (opener or urlopen)(req,timeout=90) as resp:
            wire=resp.read(MAX_RESPONSE+1)
        if len(wire)>MAX_RESPONSE:
            raise NarrationError("response exceeds limit")
        raw=extract_wav(json.loads(wire))
    except HTTPError as exc:
        raise NarrationError("Gemini HTTP %s; no retry or fallback"%exc.code) from None
    except (URLError,TimeoutError,OSError,ValueError):
        raise NarrationError("Gemini response unavailable; no retry or fallback") from None
    _atomic(path,raw)
    _atomic(seal,json.dumps({"request_sha256":cache_key,"sha256":hashlib.sha256(raw).hexdigest(),
        "model":MODEL,"voice":VOICE,**validate_wav(raw)},sort_keys=True).encode())
    return path

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--script",type=Path,required=True)
    ap.add_argument("--cache",type=Path,required=True)
    ap.add_argument("--style",default=STYLE)
    args=ap.parse_args()
    try:
        print(generate(args.script.read_text(encoding="utf-8"),args.cache,args.style))
    except (NarrationError,OSError,ValueError) as exc:
        ap.exit(2,"Narration unavailable; Reel deferred. "+str(exc)+"\n")

if __name__=="__main__":
    main()
