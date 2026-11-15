"""Bounded documentary pilot: fail closed; never grants Meta access."""
from datetime import date,datetime
from .engine import load,TZ
from .evidence import fingerprint
from .editorial_audit import inspect_files

POLICY_PATH="data/pilot_policy.json"

def window_slot(now):
    """Local recovery windows [09:00,11:00) and [17:00,19:00)."""
    local=now.astimezone(TZ)
    if 9<=local.hour<11:
        return 9
    if 17<=local.hour<19:
        return 17
    return None

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
        slot=window_slot(now)
        if slot not in p["allowed_hours"]:
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
        if any(x.date()==now.date() and window_slot(x)==slot for x in history):
            return False
        return len(history)<p["max_total"] and sum(x.date()==now.date() for x in history)<p["max_daily"]
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        return False
