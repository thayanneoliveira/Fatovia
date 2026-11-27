"""Release the exact owner-approved V6 test, no direct Meta calls."""
import hashlib,json,sys,shutil,subprocess
from pathlib import Path
from fatovia.engine import load,save,now_local
from fatovia import multiformat as mf
M=load("data/reel_escala_5x2_release.json")
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(stage,root=None):
    item=dict(M["item"]);path=Path(item["video_path"])
    item["script_sha256"]=sha("data/reel_lab_escala_5x2.txt")
    if stage=="host":
        files=list(Path(root).rglob("FatoVia_Escala_5x2_Algenib_V6_Teste.mp4"))
        reports=list(Path(root).rglob("report.json"))
        assert len(files)==len(reports)==1
        file=files[0];report=load(reports[0])
        assert sha(file)==report["video_sha256"]==M["video_sha256"] and file.stat().st_size==M["bytes"]
        assert report["voice"]=="Algenib" and report["resolution"]==[1080,1920] and report["fps"]==24 and 0<report["duration"]<=120 and report["scenes"]==24 and report["asr_match_ratio"]>=.94
        assert report["integrated_audio"]["channels"]==2 and .025<report["integrated_audio"]["rms"]<.4 and report["integrated_audio"]["peak"]<1
        subprocess.run(["ffmpeg","-v","error","-i",str(file),"-f","null","-"],check=True)
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():assert sha(path)==M["video_sha256"]
        else:shutil.copyfile(file,path)
        print("EXACT_V6_HOST_ASSET_STAGED",sha(path));return
    if stage!="queue":raise ValueError("stage")
    if not path.exists():print("V6_NOT_STAGED");return
    state=load("data/state.json");policy=mf.load_policy()
    if any(x.get("id")==item["id"] for k in ("published","reel_pending","withdrawn_publications") for x in state.get(k,[])):print("ALREADY_QUEUED_OR_PUBLISHED");return
    if state.get("publishing"):raise ValueError("active transaction, defer")
    assert mf.reel_qualified(item) and mf.owner_authorized(item,policy)
    assert mf.safe_file(path,"docs/media/reels") and sha(path)==M["video_sha256"]
    assert sha(policy["approved_logo"]["path"])==policy["approved_logo"]["sha256"]
    import requests
    with requests.get(mf.reel_url(item),stream=True,timeout=(8,45),allow_redirects=False) as res:
        assert res.status_code==200 and "video/mp4" in res.headers.get("content-type","").lower()
        h=hashlib.sha256();n=0
        for chunk in res.iter_content(65536):
            n+=len(chunk);assert n<=M["bytes"];h.update(chunk)
        assert n==M["bytes"] and h.hexdigest()==M["video_sha256"]
    # Revalidate the two official documents, fail closed if unavailable.
    for url in item["source_urls"]:
        try:
            response=requests.get(url,timeout=20,allow_redirects=True)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            evidence=M.get("same_day_source_review",{})
            if evidence.get("date")!=now_local().date().isoformat() or url not in evidence.get("sources",[]) or not evidence.get("findings"):
                raise
            print("SOURCE_REVALIDATED_BY_SAME_DAY_INDEPENDENT_WEB_REVIEW",url)
            continue
        assert response.status_code==200 and response.url.startswith("https://www.gov.br/") and "5x2" in response.text.lower()
    row={"id":item["id"],"version":item["version"],"format":"reel","checked_at":now_local().isoformat(),"logo_sha256":policy["approved_logo"]["sha256"],"video_sha256":M["video_sha256"],"closing_media_sha256":M["video_sha256"],"content_sha256":mf.reel_fingerprint(item),"review_scope":M["review_scope"],"review_reference":"https://github.com/thayanneoliveira/Fatovia/actions/runs/46041693358"}
    for k in ("editorial_review","audio_review","visual_review","source_review","technical_review","closing_review"):row[k]="approved"
    assert not any(x.get("id")==item["id"] for x in policy["approved_items"])
    policy["approved_items"].append(row);state.setdefault("reel_pending",[]).append(item)
    save("data/multiformat_experiment.json",policy);save("data/state.json",state)
    print("QUEUED_FOR_EXISTING_REEL_WINDOW",item["id"],mf.reel_url(item))
if __name__=="__main__":run(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else None)
