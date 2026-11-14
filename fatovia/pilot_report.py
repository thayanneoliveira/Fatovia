"""Pilot monitoring only. No posting, no policy activation, no causal inference."""
from datetime import date,datetime,timedelta
from .engine import TZ,load,save,now_local

def stamp(value):
    d=datetime.fromisoformat(value.replace("Z","+00:00"))
    if d.tzinfo is None:
        raise ValueError("timestamp_has_no_offset")
    return d.astimezone(TZ)

def build(state,policy,now):
    start=date.fromisoformat(policy["start_date"])
    end=date.fromisoformat(policy["end_date"])
    maximum=policy["max_total"]
    allowed={(x["id"],x["version"]) for x in policy["items"]}
    issues=[]
    rows=[]
    mids=set()
    documents=set()
    for p in state.get("published",[]):
        try:
            dt=stamp(p["published_at"])
            if not start<=dt.date()<=end:
                continue
            key=(p["id"],p["version"])
            mid=str(p["media_id"])
            if key not in allowed:
                issues.append("publication_outside_pilot_allowlist")
                continue
            if not mid.isdigit() or mid in mids or key in documents or dt>now:
                issues.append("invalid_or_duplicate_publication_record")
                continue
            mids.add(mid); documents.add(key)
            age=(now-dt).total_seconds()/3600
            row={"document_id":p["id"],"media_id":mid,"published_at":dt.isoformat(),
                 "permalink":p.get("permalink",""),"topics":p.get("topics",[]),"age_hours":round(age,2),"samples":{}}
            for target in (24,72):
                candidates=[x for x in state.get("metric_cohorts",[]) if str(x.get("media_id"))==mid and x.get("target_hours")==target]
                good=[x for x in candidates if type(x.get("age_hours")) in (int,float) and target<=x["age_hours"]<target+7
                      and all(type(x.get(k)) in (int,float) and x[k]>=0 for k in ("reach","saved","shares"))]
                if len(good)==1:
                    x=good[0]
                    row["samples"][str(target)]={"status":"collected",**{k:x[k] for k in ("age_hours","reach","saved","shares","views") if k in x}}
                else:
                    status="not_due" if age<target else ("awaiting_collection" if age<target+7 else "window_missed")
                    if len(good)>1:
                        status="ambiguous_sample"
                        issues.append("duplicate_metric_window")
                    row["samples"][str(target)]={"status":status}
            rows.append(row)
        except (KeyError,TypeError,ValueError,AttributeError):
            issues.append("invalid_publication_history")
    rows.sort(key=lambda r:r["published_at"])
    count=len(rows)
    if count>maximum:
        issues.append("pilot_total_exceeded")
    for dt in {r["published_at"][:10] for r in rows}:
        if sum(r["published_at"].startswith(dt) for r in rows)>policy["max_daily"]:
            issues.append("pilot_daily_limit_exceeded")
    if state.get("publishing"):
        status="transaction_requires_attention"
    elif issues:
        status="review_required"
    elif now.date()<start:
        status="awaiting_start"
    elif count>=maximum or now.date()>end:
        status="publication_window_closed"
    else:
        status="pilot_in_progress"
    # Even an empty or unsuccessful pilot must never unlock the next phase.
    complete={str(h):sum(r["samples"][str(h)]["status"]=="collected" for r in rows) for h in (24,72)}
    return {"generated_at":now.isoformat(),"pilot_id":policy["pilot_id"],"status":status,
            "published":count,"max_total":maximum,"remaining_allowance":max(0,maximum-count),
            "samples_collected":complete,"publications":rows,"issues":sorted(set(issues)),
            "evaluation_ready":status=="publication_window_closed" and count>0 and complete["24"]==count and complete["72"]==count,
            "next_phase_authorized":False,"limitations":"Only recorded pilot posts; no retroactive estimates, no automatic promotion, no optimization from four samples."}

def main():
    data=build(load("data/state.json"),load("data/pilot_policy.json"),now_local())
    save("data/pilot_report.json",data)
    print("PILOT_REPORT",data["status"],"published",data["published"],"samples",data["samples_collected"])
if __name__=="__main__":
    main()
