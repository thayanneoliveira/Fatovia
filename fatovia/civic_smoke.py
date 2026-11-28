"""Read-only live check; never publishes or edits the production queue."""
import json
from .engine import now_local,save
from .civic import collect,verify
from .render import render
from .evidence import seal
from .brand import approved_logo
from .editorial_audit import review
def main():
    now=now_local()
    if approved_logo() is None:raise ValueError("approved_logo_unavailable")
    rows,errors=collect(now)
    results=[]
    for item in rows:
        render(item,root="docs/media",premium=True)
        seal(item,now)
        item["status"]="ready"
        row=review(item,now,source_check=lambda i:verify(i,now))
        results.append({"id":item["id"],"observation":item["observation"],"decision":row["decision"],"issues":row["issues"]})
        if row["decision"]!="approved_documentary_only":errors[item["id"]]="audit_rejected"
    print(json.dumps({"sources":results,"errors":errors,"publication":False},ensure_ascii=False))
    if not results or any(r["decision"]!="approved_documentary_only" for r in results):raise ValueError("live_smoke_failed")
if __name__=="__main__": main()
