"""Multiformat publication gate; retains documentary evidence, exact-file authorization and shared state."""
import hashlib
import json
import re
from datetime import date,datetime,timedelta
from pathlib import Path
from urllib.parse import quote
from .engine import TZ
from .evidence import fingerprint
from .editorial_audit import inspect_files, approved
from .brand import approved_logo

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
def transition_authorized(state,now,policy):
    """A documented incident closure is not authorization to bypass reconciliation."""
    from .pilot_report import build
    try:
        pilot=json.loads(Path("data/pilot_policy.json").read_text(encoding="utf-8"))
        report=build(state,pilot,now)
        approval=policy.get("pilot_transition") or {}
        if not (approval.get("authorized") is True
                and approval.get("pilot_id")==report["pilot_id"]
                and isinstance(approval.get("review_reference"),str)
                and bool(approval["review_reference"].strip())
                and approval.get("reviewed_media_ids")==[r["media_id"] for r in report["publications"]]):
            return False
        if report["evaluation_ready"] is True and not report["issues"]:
            return True
        closure=json.loads(Path("data/pilot_incident_closure_20261121.json").read_text(encoding="utf-8"))
        reconciliation=closure.get("reconciliation") or {}
        return (closure.get("pilot_id")==report["pilot_id"]
                and closure.get("closure_type")=="closed_with_incident"
                and closure.get("incident_preserved") is True
                and closure.get("legacy_history_must_remain") is True
                and closure.get("observed_pilot_count")==report["published"]
                and set(closure.get("issues",[]))==set(report["issues"])
                and reconciliation.get("status")=="verified_against_live_meta"
                and reconciliation.get("account_id_verified") is True
                and reconciliation.get("media_ids_verified")==[r["media_id"] for r in report["publications"]]
                and closure.get("production_transition_authorized") is True)
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        return False
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
def owner_authorized(item, policy):
    """Owner's per-content scope is necessary, never sufficient, for publication."""
    authorization = policy.get("owner_per_content_authorization") or {}
    if authorization.get("decision") != "authorized_by_owner_pending_operational_validation":
        return False
    if authorization.get("max_spend_brl") != 0 or authorization.get("daily_caps") != CAPS:
        return False
    item_id = item.get("id")
    if not isinstance(item_id, str) or item_id in authorization.get("excluded_ids", []):
        return False
    fmt = kind(item)
    if fmt not in CAPS:
        return False
    ids = authorization.get("reel_ids" if fmt == "reel" else "carousel_ids", [])
    return isinstance(ids, list) and ids.count(item_id) == 1

def allowed(state,item,now,policy=None):
    try:
        p=load_policy() if policy is None else policy
        fmt=kind(item)
        if (not owner_authorized(item,p) or not transition_authorized(state,now,p) or p["status"] not in ("prepared_guarded", "approved") or p["daily_caps"]!=CAPS or p["max_spend_brl"]!=0
                or now.astimezone(TZ).date()<date.fromisoformat(p["start_date"]) or not quota(state,now,fmt)):
            return False
        if any((x["id"],x["version"])==(item["id"],item["version"]) for x in state.get("published",[])):return False
        logo=p["approved_logo"]
        if not valid_hash(logo["sha256"]) or not safe_file(logo["path"],"assets") or sha_file(logo["path"])!=logo["sha256"]:return False
        if approved_logo() is None:return False
        if fmt=="carousel":
            # Independent auditor reconstructs actual final card with approved logo, checks live evidence,
            # then binds both the source-content seal and exact rendered bytes.
            if item.get("template_revision")!="didactic-v4" or not approved(item,now):return False
            report=json.loads(Path("data/editorial_audit.json").read_text(encoding="utf-8"))
            reviews=[r for r in report["reviews"] if (r["id"],r["version"])==(item["id"],item["version"])]
            return len(reviews)==1 and reviews[0].get("logo_sha256")==logo["sha256"] and reviews[0].get("closing_media_sha256")==inspect_files(item)[-1]
        # One-time owner editorial exception: exact approved Maria v2 streams were
        # remuxed without re-encoding. This does not waive media, logo, quota,
        # Meta account, hosting, or duplicate checks.
        if item.get("id")=="reel:inflacao-precos-20261118":
            queue=json.loads(Path("data/reel_delivery_queue.json").read_text(encoding="utf-8"))
            entries=[x for x in queue.get("items",[]) if x.get("id")==item["id"]]
            if len(entries)!=1:return False
            entry=entries[0]
            auth=entry.get("exceptional_owner_authorization") or {}
            override=p.get("reel_editorial_override") or {}
            hosted=override.get("hosted_media") or {}
            owner=override.get("owner_approval") or {}
            if not (auth.get("authorized") is True and auth.get("scope")=="one_time_editorial_approval_only"
                    and auth.get("approved_asset_sha256")==owner.get("sha256")
                    and owner.get("decision")=="approved_for_publication"
                    and hosted.get("status")=="verified_stream_identical_remux_hosted"
                    and hosted.get("original_approved_sha256")==owner.get("sha256")
                    and hosted.get("path")==item.get("video_path")
                    and hosted.get("sha256")==item.get("video_sha256")
                    and hosted.get("video_stream_sha256") and hosted.get("audio_stream_sha256")
                    and reel_qualified(item) and item.get("source_urls")
                    and valid_hash(item.get("script_sha256"))):return False
            path=video_path(item)
            return (safe_file(path,"docs/media/reels") and Path(path).stat().st_size<=MAX_VIDEO
                    and valid_hash(hosted["sha256"]) and sha_file(path)==hosted["sha256"])
        rows=[r for r in p["approved_items"] if (r["id"],r["version"],r["format"])==(item["id"],item["version"],fmt)]
        if len(rows)!=1:return False
        r=rows[0]
        checked=datetime.fromisoformat(r["checked_at"])
        if not now-timedelta(hours=24)<=checked<=now or r["logo_sha256"]!=logo["sha256"] or r["closing_review"]!="approved":return False
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
