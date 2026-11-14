"""Bounded documentary pilot: fail closed; never grants Meta access."""
from datetime import date,datetime
from .engine import load,TZ
from .evidence import fingerprint
from .editorial_audit import inspect_files

POLICY_PATH="data/pilot_policy.json"

def allowed(state,item,now,policy=None):
    try:
        p=load(POLICY_PATH) if policy is None else policy
        if p.get("schema")!=1 or p.get("status")!="prepared":
            return False
        start=date.fromisoformat(p["start_date"])
        end=date.fromisoformat(p["end_date"])
        if not start<=now.date()<=end or (end-start).days>6:
            return False
        if p["max_total"]!=4 or p["max_daily"]!=2 or p["allowed_hours"]!=[9,17]:
            return False
        if now.hour not in p["allowed_hours"] or now.minute>45:
            return False
        if item.get("template_revision")!=p["template_revision"]:
            return False
        allowed_rows=[r for r in p["items"] if (r["id"],r["version"])==(item["id"],item["version"])]
        if len(allowed_rows)!=1:
            return False
        row=allowed_rows[0]
        if row["content_sha256"]!=fingerprint(item) or row["card_sha256"]!=inspect_files(item):
            return False
        history=[]
        for old in state.get("published",[]):
            if not old.get("published_at"):
                # Historical records without a timestamp cannot be used to certify quotas.
                return False
            stamp=datetime.fromisoformat(old["published_at"].replace("Z","+00:00")).astimezone(TZ)
            if start<=stamp.date()<=end:
                history.append(stamp)
        return len(history)<p["max_total"] and sum(x.date()==now.date() for x in history)<p["max_daily"]
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        return False
