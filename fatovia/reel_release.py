"""Two-stage release: explicit independent review, then exact public-byte verification.
No Meta calls. Writes only the specific reviewed episode; publishing remains separate.
"""
import argparse,hashlib,re,shutil
from datetime import datetime
from pathlib import Path
import requests
from .engine import load,save,now_local
from .evidence import verify_live
from .editorial_audit import approved
from .reel_factory import build_plan
from .didactic import reviewed
from . import multiformat as mf
REVIEWS=("editorial_review","audio_review","visual_review","source_review","technical_review","closing_review")
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def release(bundle,review,stage,now=None,source_check=verify_live,editorial_check=approved):
    now=now or now_local();bundle=Path(bundle);plan=load(bundle/"plan.json");report=load(bundle/"report.json")
    item=plan["source"]
    if not editorial_check(item,now) or not source_check(item):raise ValueError("source review expired or changed")
    if plan!=build_plan(item,reviewed(item)):raise ValueError("plan not reconstructible from reviewed source")
    file=bundle/"reel.mp4";digest=sha(file);policy=load("data/multiformat_experiment.json");state=load("data/state.json")
    if not (review.get("reviewer") and review.get("scope")=="independent_final_media" and all(review.get(k)=="approved" for k in REVIEWS)
        and review.get("video_sha256")==report.get("video_sha256")==digest and review.get("script_sha256")==report.get("script_sha256")==plan["script_sha256"]
        and review.get("caption_sha256")==report.get("caption_sha256")==hashlib.sha256(plan["caption"].encode()).hexdigest()
        and review.get("logo_sha256")==report.get("logo_sha256")==policy["approved_logo"]["sha256"]
        and report.get("voice")=="Algenib" and report.get("visual_revision")=="V6" and report.get("asr_match",0)>=.94
        and 0<report.get("duration",0)<=120 and report.get("shots",0)>=12 and report.get("resolution")==[1080,1920] and report.get("fps")==24
        and .025<report.get("rms",0)<.4 and 0<report.get("peak",0)<1
        and file.stat().st_size<=mf.MAX_VIDEO and datetime.fromisoformat(review["checked_at"])<=now):raise ValueError("independent review or technical binding missing")
    ident=plan["id"];ver=plan["version"]
    if not re.fullmatch(r"reel:[a-z0-9_-]+",ident) or not re.fullmatch(r"[0-9a-f]{14}",ver):raise ValueError("identity")
    if state.get("publishing"):raise ValueError("active transaction; defer Reel only")
    if any(x.get("id") in (ident,item["id"]) for k in ("published","reel_pending","withdrawn_publications") for x in state.get(k,[])):raise ValueError("already used source")
    path=Path("docs/media/reels")/(ident.replace(":","-")+"-"+ver+".mp4")
    if stage not in ("host","queue"):raise ValueError("stage")
    if stage=="host":
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.is_symlink() or (path.exists() and sha(path)!=digest):raise ValueError("conflicting host asset")
        shutil.copyfile(file,path)
        return {"status":"host_staged","path":str(path),"sha256":digest}
    if not mf.safe_file(path,"docs/media/reels") or sha(path)!=digest:raise ValueError("not hosted locally")
    ready={"id":ident,"version":ver,"format":"reel","status":"ready","caption":plan["caption"],"voice":"Algenib","visual_revision":"V6","source_urls":[item["source_url"],item["public_url"]],"script_sha256":plan["script_sha256"],"video_sha256":digest,"video_path":str(path),"topics":item["topics"],"title":plan["hook"],"editorial_score":item.get("editorial_score",0)}
    if not mf.reel_qualified(ready) or not mf.owner_authorized(ready,policy):raise ValueError("publisher not authorized")
    with requests.get(mf.reel_url(ready),stream=True,timeout=(8,45),allow_redirects=False) as response:
        if response.status_code!=200 or "video/mp4" not in response.headers.get("content-type","").lower():raise ValueError("public MP4 absent")
        h=hashlib.sha256();n=0
        for block in response.iter_content(65536):
            n+=len(block)
            if n>mf.MAX_VIDEO:raise ValueError("public size")
            h.update(block)
        if n!=file.stat().st_size or h.hexdigest()!=digest:raise ValueError("public bytes mismatch")
    row={"id":ident,"version":ver,"format":"reel","checked_at":review["checked_at"],"logo_sha256":review["logo_sha256"],"video_sha256":digest,"closing_media_sha256":digest,"content_sha256":mf.reel_fingerprint(ready),**{k:review[k] for k in REVIEWS}}
    if any(x.get("id")==ident for x in policy["approved_items"]):raise ValueError("existing approval")
    policy["approved_items"].append(row);state.setdefault("reel_pending",[]).append(ready)
    save("data/multiformat_experiment.json",policy);save("data/state.json",state)
    return {"status":"queued_after_host_verification","id":ident,"sha256":digest}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--bundle",required=True);ap.add_argument("--review",required=True);ap.add_argument("--stage",choices=["host","queue"],required=True);args=ap.parse_args()
    print(release(args.bundle,load(args.review),args.stage))
if __name__=="__main__":main()
