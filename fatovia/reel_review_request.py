"""Validate trusted review requests and factory run provenance, no publication."""
import argparse, hashlib, json, re, sys
from pathlib import Path
from datetime import datetime, timezone
REVIEW_FIELDS=("editorial_review","audio_review","visual_review","source_review","technical_review","closing_review")
def validate(row,now=None):
    now=now or datetime.now(timezone.utc)
    if type(row.get("run_id")) is not int or row["run_id"]<=0:raise ValueError("factory run ID")
    if row.get("scope")!="independent_final_media" or not isinstance(row.get("reviewer"),str) or not row["reviewer"].strip():raise ValueError("review identity")
    if any(row.get(k)!="approved" for k in REVIEW_FIELDS):raise ValueError("review incomplete")
    for k in ("video_sha256","script_sha256","caption_sha256","logo_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}",str(row.get(k,""))):raise ValueError("review hash")
    t=datetime.fromisoformat(row["checked_at"])
    if t.tzinfo is None or not 0<=(now-t).total_seconds()<=86400:raise ValueError("review time")
    if not isinstance(row.get("review_evidence"),dict) or any(not isinstance(row["review_evidence"].get(k),str) or not row["review_evidence"][k].strip() for k in REVIEW_FIELDS):raise ValueError("review evidence absent")
    return row
def provenance(run):
    if run.get("head_branch")!="main" or run.get("status")!="completed" or run.get("conclusion")!="success" or run.get("path")!=".github/workflows/reel-factory.yml" or (run.get("head_repository") or {}).get("full_name","").lower()!="thayanneoliveira/fatovia":raise ValueError("untrusted factory run")
def main():
    p=argparse.ArgumentParser();p.add_argument("--request",type=Path);p.add_argument("--output",type=Path);p.add_argument("--provenance",action="store_true");a=p.parse_args()
    if a.provenance:provenance(json.load(sys.stdin));return
    if not a.request or not a.output:raise ValueError("request and output")
    raw=a.request.read_bytes();row=validate(json.loads(raw))
    with a.output.open("a") as f:f.write("run_id="+str(row["run_id"])+"\nreview_sha="+hashlib.sha256(raw).hexdigest()+"\n")
if __name__=="__main__":main()
