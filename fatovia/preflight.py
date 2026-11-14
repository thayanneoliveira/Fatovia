"""Read-only end-to-end check: no Meta credentials, no POST and no queue modification."""
import json
from .engine import load,now_local,save
from .editorial_audit import approved,verify_hosted
from .evidence import verify_live
from .publisher import qualified

def run(state,now,source_check=verify_live,host_check=verify_hosted):
    rows=[]
    for item in state.get("pending",[])[:8]:
        row={"id":item.get("id"),"title":item.get("title"),"checks":{}}
        checks=row["checks"]
        checks["publisher_rules"]=qualified(item,now)
        checks["independent_audit"]=approved(item,now)
        checks["source_live"]=source_check(item) if checks["publisher_rules"] and checks["independent_audit"] else False
        checks["hosted_bytes"]=host_check(item,now) if checks["source_live"] else False
        row["ready_for_documentary_pilot"]=all(checks.values())
        rows.append(row)
    return {"generated_at":now.isoformat(),"rows":rows,"ready":sum(r["ready_for_documentary_pilot"] for r in rows),
            "publication_authorized":False,"meta_posts_sent":0,
            "limitations":"Technical preflight for documentary template only, not creative or semantic approval."}

def main():
    report=run(load("data/state.json"),now_local())
    save("data/preflight_report.json",report)
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":
    main()
