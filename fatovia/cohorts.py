"""Collect comparable 24h/72h samples from account-owned media.
Missing metrics remain absent; no post or account changes.
"""
from datetime import datetime, timezone
import os
import re
import requests
from .engine import daily_limit, preferred_hours

BASE = "https://graph.instagram.com/v25.0/"
METRICS = ("reach", "saved", "shares", "views")
WINDOWS = ((24, 24, 31), (72, 72, 79))


def age_bucket(hours):
    return next((label for label, low, high in WINDOWS if low <= hours < high), None)


def extract(payload, name):
    for item in payload.get("data", []):
        if item.get("name") != name:
            continue
        values = item.get("values")
        value = values[0].get("value") if isinstance(values, list) and values else item.get("total_value", {}).get("value")
        if type(value) in (int, float) and value >= 0:
            return int(value)
    return None


def collect(state, now, client=None):
    token = os.getenv("META_ACCESS_TOKEN", "")
    ig = os.getenv("META_IG_USER_ID", "")
    if client is None:
        if not token or not re.fullmatch(r"[0-9]{5,30}", ig):
            raise ValueError("missing configuration")
        session = requests.Session()
        def client(path, params):
            try:
                r = session.get(BASE + path, params=params,
                                headers={"Authorization": "Bearer "+token},
                                timeout=(5, 12), allow_redirects=False)
                return r.json() if r.status_code == 200 else {}
            except (requests.RequestException, ValueError):
                return {}
    me = client("me", {"fields": "user_id,username"})
    if str(me.get("user_id")) != ig or str(me.get("username","")).lower() != "fato.via":
        raise ValueError("account mismatch")
    media = client(ig + "/media", {"fields": "id,media_type,timestamp", "limit": 50})
    if not isinstance(media.get("data"), list):
        raise ValueError("media list unavailable")
    samples = { (row["media_id"], row["target_hours"]): row for row in state.get("metric_cohorts", [])
               if isinstance(row, dict) and "media_id" in row and "target_hours" in row }
    metadata = {str(p.get("media_id")):p for p in state.get("published", [])}
    attempts = 0
    for m in media["data"]:
        mid = str(m.get("id",""))
        if not re.fullmatch(r"[0-9]{5,30}", mid):
            continue
        try:
            dt = datetime.fromisoformat(m["timestamp"].replace("Z","+00:00"))
            age = (now-dt).total_seconds()/3600
        except (ValueError, KeyError, TypeError):
            continue
        target = age_bucket(age)
        if target is None or (mid,target) in samples:
            continue
        values = {}
        for name in METRICS:
            value = extract(client(mid+"/insights", {"metric": name}), name)
            if value is not None:
                values[name] = value
        attempts += 1
        if not all(name in values for name in ("reach","saved","shares")):
            continue
        samples[mid,target] = {"media_id":mid,"target_hours":target,"age_hours":round(age,2),
            "observed_at":now.isoformat(),"published_at":dt.isoformat(),"media_type":m.get("media_type"),
            "topics":metadata.get(mid,{}).get("topics", []),**values}
    state["metric_cohorts"] = sorted(samples.values(), key=lambda x:x["observed_at"])[-240:]
    return {"recent_media":len(media["data"]), "attempted":attempts,
            "samples_24h":sum(s["target_hours"]==24 for s in samples.values()),
            "samples_72h":sum(s["target_hours"]==72 for s in samples.values()),
            "note":"No retroactive reconstruction of missing age windows; incomplete samples excluded."}


def learning_report(state):
    cohort = [x for x in state.get("metric_cohorts",[]) if x.get("target_hours")==72
              and all(type(x.get(k)) in (int,float) for k in ("reach","saved","shares"))
              and x["reach"]>=20]
    if len(cohort)<20:
        return {"status":"insufficient_sample","eligible_72h":len(cohort),"min_samples":20,
                "recommended_daily_limit":daily_limit(state),"recommended_hours":preferred_hours(state)}
    # Descriptive only; do not treat correlation as causal or override editorial safeguards.
    return {"status":"descriptive_only","eligible_72h":len(cohort),
            "mean_useful_interactions_per_reach":round(sum((x["saved"]+x["shares"])/x["reach"] for x in cohort)/len(cohort),4),
            "recommended_daily_limit":daily_limit(state),"recommended_hours":preferred_hours(state)}
