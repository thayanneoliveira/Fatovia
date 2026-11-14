"""Official SIDRA series, with strict metric and geographic provenance."""
import json
import re
from decimal import Decimal
from datetime import datetime
from hashlib import sha256
from .discovery import get
from .engine import now_local,save
from .budget import norm

SPECS={
    "ipca_monthly":{"table":"1737","variable":"63","frequency":"monthly","count":12,
        "label":"IPCA - Variação mensal","label_terms":["ipca","variacao mensal"],
        "unit":"%","period_digits":6,"max_age_months":2,
        "limitation":"Índice geral nacional mensal; não representa inflação individual, núcleo ou acumulado anual."},
    "unemployment_quarterly":{"table":"4099","variable":"4099","frequency":"quarterly","count":8,
        "label":"Taxa de desocupação","label_terms":["taxa de desocupacao"],
        "unit":"%","period_digits":5,"max_age_months":9,
        "limitation":"PNAD Contínua trimestral, pessoas de 14 anos ou mais; não é número absoluto de pessoas nem taxa mensal."}
}

def parse(raw,spec,now):
    rows=json.loads(raw)
    if not isinstance(rows,list) or len(rows)<2 or len(rows)>spec["count"]+1:
        raise ValueError("invalid_series_length")
    header=rows[0]
    if not isinstance(header,dict):
        raise ValueError("invalid_header")
    # Locate dimensions using SIDRA's own labels instead of assuming D1, D2, D3 order.
    def dimension(predicate):
        matches=[k[:-1] for k,v in header.items() if re.fullmatch(r"D\d+N",k) and predicate(norm(v))]
        if len(matches)!=1:
            raise ValueError("dimension_mismatch")
        return matches[0]
    geography=dimension(lambda x:"brasil" in x or "nivel territorial" in x)
    variable=dimension(lambda x:x=="variavel")
    period=dimension(lambda x:x==("mes" if spec["frequency"]=="monthly" else "trimestre"))
    items={}
    unavailable=[]
    for row in rows[1:]:
        if not isinstance(row,dict) or str(row.get(geography+"C"))!="1" or norm(row.get(geography+"N"))!="brasil":
            raise ValueError("geography_mismatch")
        if str(row.get(variable+"C"))!=spec["variable"] or not all(t in norm(row.get(variable+"N")) for t in spec["label_terms"]):
            raise ValueError("variable_mismatch")
        if row.get("MN")!=spec["unit"]:
            raise ValueError("unit_mismatch")
        key=str(row.get(period+"C",""))
        if not re.fullmatch(r"\d{"+str(spec["period_digits"])+"}",key):
            # SIDRA quarter codes may be YYYYQQ (01..04).
            if spec["frequency"]!="quarterly" or not re.fullmatch(r"\d{6}",key):
                raise ValueError("period_mismatch")
        year=int(key[:4]); sub=int(key[4:])
        if not 1<=sub<=(12 if spec["frequency"]=="monthly" else 4):
            raise ValueError("invalid_period")
        end_month=sub if spec["frequency"]=="monthly" else sub*3
        age=(now.year-year)*12+now.month-end_month
        if age<0:
            raise ValueError("future_period")
        canonical=f"{year:04d}-{sub:02d}" if spec["frequency"]=="monthly" else f"{year:04d}-Q{sub}"
        if canonical in items or canonical in unavailable:
            raise ValueError("duplicate_period")
        value=row.get("V")
        if value in ("-","..","...","X",None):
            unavailable.append(canonical)
            continue
        if not isinstance(value,str) or not re.fullmatch(r"-?\d{1,6}(?:\.\d{1,10})?",value):
            raise ValueError("invalid_value")
        if not Decimal(value).is_finite():
            raise ValueError("invalid_value")
        items[canonical]={"period":canonical,"source_period":key,"period_label":row.get(period+"N"),
                          "value":value,"age_months":age}
    observations=[items[k] for k in sorted(items)]
    status="unavailable" if not observations else ("ok" if observations[-1]["age_months"]<=spec["max_age_months"] else "stale")
    return {"status":status,"observations":observations,"missing_periods":sorted(unavailable),"geography":"Brasil"}

def collect(now,getter=get):
    result={}
    for key,spec in SPECS.items():
        url=f"https://apisidra.ibge.gov.br/values/t/{spec['table']}/n1/all/v/{spec['variable']}/p/last%20{spec['count']}"
        item={**spec,"source_url":url,"metadata_url":f"https://sidra.ibge.gov.br/tabela/{spec['table']}",
              "retrieved_at":now.isoformat(),"publication_authorized":False}
        try:
            raw=getter(url)
            item.update(parse(raw,spec,now),response_sha256=sha256(raw).hexdigest())
        except Exception as exc:
            item.update(status="unavailable",error_type=type(exc).__name__)
            if isinstance(exc,ValueError) and re.fullmatch(r"[a-z_0-9]+",str(exc)):
                item["error_code"]=str(exc)
            if "raw" in locals():
                try:
                    rows=json.loads(raw)
                    if isinstance(rows,list) and rows and isinstance(rows[0],dict):
                        item["observed_header"]={k:str(v)[:150] for k,v in rows[0].items()}
                except Exception:
                    pass
        result[key]=item
        if "raw" in locals():
            del raw
    return {"generated_at":now.isoformat(),"series":result,"publication_authorized":False,
            "limitations":["No causal attribution","No mixing monthly and quarterly observations","Missing values are not zero","Survey estimates may be revised"]}

def main():
    report=collect(now_local())
    save("data/ibge_context.json",report)
    print(json.dumps({key:{"status":v["status"],"observations":len(v.get("observations",[])),"error_code":v.get("error_code")}
                      for key,v in report["series"].items()}))
if __name__=="__main__":
    main()
