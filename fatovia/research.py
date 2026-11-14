"""Public economic context, not a policy attribution or publication approval."""
from datetime import datetime,timedelta
from decimal import Decimal,InvalidOperation
from hashlib import sha256
import json
import re
from .discovery import get
from .engine import now_local,save

SERIES={
  "432":{"name":"Meta Selic definida pelo Copom","frequency":"daily","unit":"% a.a.","max_age_days":7,"count":30,
         "metadata":"https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom",
         "limitation":"Meta anualizada, não taxa efetiva de empréstimos nem rendimento diário."},
  "16122":{"name":"IPCA - núcleo de dupla ponderação","frequency":"monthly","unit":"% mensal","max_age_days":75,"count":12,
         "metadata":"https://dadosabertos.bcb.gov.br/dataset/16122-indice-nacional-de-precos-ao-consumidor---amplo-ipca---nucleo-de-dupla-ponderacao",
         "limitation":"Medida de núcleo, não IPCA cheio nem inflação particular de cada família."}
}

def parse(raw,code,now):
    spec=SERIES[code]
    rows=json.loads(raw)
    if not isinstance(rows,list) or not rows or len(rows)>spec["count"]:
        raise ValueError("invalid_series_length")
    seen={}
    for row in rows:
        if not isinstance(row,dict) or not isinstance(row.get("data"),str) or not isinstance(row.get("valor"),str):
            raise ValueError("invalid_row")
        day=datetime.strptime(row["data"],"%d/%m/%Y").date()
        if day>now.date():
            raise ValueError("future_observation")
        value=row["valor"]
        if not re.fullmatch(r"-?\d{1,6}(?:\.\d{1,10})?",value):
            raise ValueError("invalid_decimal")
        number=Decimal(value)
        if not number.is_finite():
            raise ValueError("nonfinite")
        period=day.isoformat() if spec["frequency"]=="daily" else day.strftime("%Y-%m")
        if period in seen:
            raise ValueError("duplicate_period")
        seen[period]={"period":period,"source_date":day.isoformat(),"value":value}
    observations=[seen[k] for k in sorted(seen)]
    date=datetime.fromisoformat(observations[-1]["source_date"]).date()
    status="ok" if (now.date()-date).days<=spec["max_age_days"] else "stale"
    return observations,status

def collect(now,getter=get):
    result={}
    for code,spec in SERIES.items():
        url=f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados/ultimos/{spec['count']}"
        params={"formato":"json"}
        if code=="432":
            url="https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados"
            params.update(dataInicial=(now-timedelta(days=29)).strftime("%d/%m/%Y"),dataFinal=now.strftime("%d/%m/%Y"))
        entry={"series":code,**spec,"source_url":url,"retrieved_at":now.isoformat(),"query_params":params,
               "use":"economic_context_only","publication_authorized":False}
        try:
            raw=getter(url,params)
            observations,status=parse(raw,code,now)
            entry.update(status=status,observations=observations,response_sha256=sha256(raw).hexdigest())
        except Exception as exc:
            entry.update(status="unavailable",error_type=type(exc).__name__)
            if isinstance(exc,ValueError) and re.fullmatch(r"(?:invalid_[a-z_]+|future_observation|duplicate_period|nonfinite|source_http_\d+|source_too_large)",str(exc)):
                entry["error_code"]=str(exc)
        result[code]=entry
    return {"generated_at":now.isoformat(),"series":result,"publication_authorized":False,
            "limitations":["No causal attribution","No comparison across unlike units or frequencies",
                           "Observation dates are not necessarily release dates","Revisions may occur"]}

def main():
    report=collect(now_local())
    save("data/economic_context.json",report)
    print(json.dumps({code:{"status":v["status"],"observations":len(v.get("observations",[]))}
                      for code,v in report["series"].items()}))
if __name__=="__main__":
    main()
