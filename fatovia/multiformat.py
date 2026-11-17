"""Multiformat publication gate; retains documentary evidence, exact-file authorization and shared state."""
import hashlib
import json
import re
from datetime import date,datetime,timedelta
from pathlib import Path
from urllib.parse import quote
from .engine import TZ
from .evidence import fingerprint
from .editorial_audit import inspect_files

POLICY=Path("data/multiformat_experiment.json")
SLOTS={8:"carousel",11:"carousel",14:"reel",17:"carousel",20:"carousel"}
CAPS={"carousel":4,"reel":1}
PAGE_ROOT="https://thayanneoliveira.github.io/Fatovia"
MAX_VIDEO=95_000_000

def load_policy():
    return json.loads(POLICY.read_text(encoding="utf-8"))
def mode(now):
    # Fixed migration boundary prevents fall-back to the retired pilot if policy becomes corrupt.
    return now.astimezone(TZ).date()>=date(2026,11,18)
def kind(item):
    return item.get("format","carousel")
def sha_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(65536),b""):h.update(chunk)
    return h.hexdigest()
def safe_file(path,root):
    p=Path(path)
    return not p.is_symlink() and p.is_file() and p.resolve().is_relative_to(Path(root).resolve())
def valid_hash(value):
    return isinstance(value,str) and bool(re.fullmatch(r"[a-f0-9]{64}",value))
def slot(now):
    local=now.astimezone(TZ)
    return SLOTS.get(local.hour) if local.minute<=45 else None
def quota(state,now,fmt):
    if slot(now)!=fmt or now.astimezone(TZ).date().isoformat() in state.get("blackout_dates",[]):return False
    history=[]
    for p in state.get("published",[]):
        stamp=datetime.fromisoformat(p["published_at"].replace("Z","+00:00")).astimezone(TZ)
        if stamp.date()==now.astimezone(TZ).date():
            if kind(p) not in CAPS:return False
            history.append((stamp,kind(p)))
    return (sum(f==fmt for _,f in history)<CAPS[fmt] and
            len(history)<5 and
            not any(t.hour==now.astimezone(TZ).hour for t,_ in history) and
            not any(now-t<timedelta(hours=3) for t,_ in history))
def video_path(item):
    path=item["video_path"]
    if not isinstance(path,str) or not re.fullmatch(r"docs/media/reels/[A-Za-z0-9_-]+\.mp4",path):
        raise ValueError("invalid video path")
    return path
def reel_url(item):
    return PAGE_ROOT+"/"+quote(video_path(item).removeprefix("docs/"),safe="/")
def reel_qualified(item):
    return (kind(item)=="reel" and item.get("status")=="ready" and
            re.fullmatch(r"reel:[a-z0-9_-]+",item.get("id","")) and
            re.fullmatch(r"[a-f0-9]{14}",item.get("version","")) and
            isinstance(item.get("caption"),str) and 50<=len(item["caption"])<=2200 and
            f'ID editorial: {item["id"]}/{item["version"]}' in item["caption"].splitlines() and
            item.get("voice")=="Santa-R-1.0" and item.get("visual_revision")=="V5")
def reel_fingerprint(item):
    keys=("id","version","caption","video_path","voice","visual_revision","source_urls","script_sha256")
    return hashlib.sha256(json.dumps({k:item[k] for k in keys},sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
def allowed(state,item,now,policy=None):
    try:
        p=load_policy() if policy is None else policy
        fmt=kind(item)
        if (p["status"]!="prepared_guarded" or p["daily_caps"]!=CAPS or p["max_spend_brl"]!=0
                or now.astimezone(TZ).date()<date.fromisoformat(p["start_date"]) or not quota(state,now,fmt)):
            return False
        if any((x["id"],x["version"])==(item["id"],item["version"]) for x in state.get("published",[])):return False
        logo=p["approved_logo"]
        if not valid_hash(logo["sha256"]) or not safe_file(logo["path"],"assets") or sha_file(logo["path"])!=logo["sha256"]:return False
        rows=[r for r in p["approved_items"] if (r["id"],r["version"],r["format"])==(item["id"],item["version"],fmt)]
        if len(rows)!=1:return False
        r=rows[0]
        checked=datetime.fromisoformat(r["checked_at"])
        if not now-timedelta(hours=24)<=checked<=now or r["logo_sha256"]!=logo["sha256"] or r["closing_review"]!="approved":return False
        if fmt=="carousel":
            hashes=inspect_files(item)
            return (item.get("template_revision")=="didactic-v4" and r["content_sha256"]==fingerprint(item)
                    and r["card_sha256"]==hashes and r["closing_media_sha256"]==hashes[-1])
        if not reel_qualified(item) or not item.get("source_urls") or not valid_hash(item.get("script_sha256")):return False
        path=video_path(item)
        return (r["content_sha256"]==reel_fingerprint(item) and r["editorial_review"]=="approved"
                and r["audio_review"]=="approved" and r["visual_review"]=="approved"
                and r["source_review"]=="approved" and r["technical_review"]=="approved"
                and safe_file(path,"docs/media/reels") and Path(path).stat().st_size<=MAX_VIDEO
                and valid_hash(r["video_sha256"]) and sha_file(path)==r["video_sha256"]
                and r["closing_media_sha256"]==r["video_sha256"])
    except (OSError,ValueError,TypeError,KeyError,AttributeError,IndexError):
        return False

def verify_reel_hosted(item,now,state,http=None):
    import requests
    if not allowed(state,item,now):return False
    try:
        session=http or requests.Session()
        expected=sha_file(video_path(item))
        h=hashlib.sha256();n=0
        with session.get(reel_url(item),stream=True,timeout=(8,45),allow_redirects=False) as response:
            if response.status_code!=200 or "video/mp4" not in response.headers.get("content-type","").lower():return False
            for block in response.iter_content(65536):
                n+=len(block)
                if n>MAX_VIDEO:return False
                h.update(block)
        return n>0 and h.hexdigest()==expected
    except Exception:return False
