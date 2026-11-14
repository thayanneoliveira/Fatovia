"""RREO Anexo 01, União: raw reported cells, not spending totals or causal proof."""
import calendar
import hashlib
import json
import re
import unicodedata
from datetime import date,timedelta
from decimal import Decimal
from .discovery import get
from .engine import now_local,save

URL="https://apidatalake.tesouro.gov.br/ords/cdwhprd/siconfi/tt/rreo"
ANEXO="RREO-Anexo 01"
MAX_ROWS=5000
def norm(value):
    return " ".join("".join(c for c in unicodedata.normalize("NFKD",str(value).casefold()) if not unicodedata.combining(c)).split())

def latest_due(today):
    # The regular 30-day reporting deadline is a search heuristic, not proof of delivery.
    for year in (today.year,today.year-1):
        for period in range(6,0,-1):
            month=period*2
            end=date(year,month,calendar.monthrange(year,month)[1])
            if end+timedelta(days=30)<=today:
                return year,period,end
    raise ValueError("period_unavailable")

def stage_for(column):
    s=norm(column)
    if "dotacao atualizada" in s:
        return "dotacao_atualizada"
    if "dotacao inicial" in s:
        return "dotacao_inicial"
    # Restrict to year-to-date columns, never mix bimonthly with cumulative flows.
    if "ate o bimestre" in s:
        for term,stage in (("despesas empenhadas","empenhado"),("despesas liquidadas","liquidado"),("despesas pagas","pago")):
            if term in s:
                return stage
    return None

def parse(raw,year,period):
    data=json.loads(raw,parse_float=Decimal)
    if not isinstance(data,dict) or not isinstance(data.get("items"),list):
        raise ValueError("invalid_payload")
    rows=data["items"]
    if not rows:
        raise ValueError("empty_report")
    if len(rows)>MAX_ROWS or data.get("hasMore") is not False:
        raise ValueError("incomplete_report")
    cells=[]
    keys=set()
    columns=set()
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError("invalid_row")
        if str(row.get("exercicio"))!=str(year) or str(row.get("periodo"))!=str(period):
            raise ValueError("period_mismatch")
        if str(row.get("cod_ibge"))!="1" or norm(row.get("instituicao","")) not in {"uniao","governo federal"} or row.get("esfera")!="U":
            raise ValueError("entity_mismatch")
        if norm(row.get("anexo"))!=norm(ANEXO):
            raise ValueError("annex_mismatch")
        col=row.get("coluna")
        if not isinstance(col,str):
            raise ValueError("invalid_column")
        columns.add(col)
        stage=stage_for(col)
        # Never match a receipt/percentage/ratio column or infer missing cells.
        if not stage:
            continue
        account=row.get("conta")
        code=row.get("cod_conta")
        label=row.get("rotulo")
        if not all(isinstance(v,str) and v.strip() for v in (account,code,label)):
            raise ValueError("missing_account_identity")
        # Anexo 01 may contain both receipts and expenses; keep labels verbatim.
        value=row.get("valor")
        if value is None:
            continue
        if isinstance(value,bool) or not isinstance(value,(str,int,Decimal)):
            raise ValueError("invalid_value")
        number=Decimal(str(value))
        if not number.is_finite():
            raise ValueError("invalid_value")
        identity=(label,code,account,col)
        if identity in keys:
            raise ValueError("duplicate_cell")
        keys.add(identity)
        cells.append({"rotulo":label,"cod_conta":code,"conta":account,"coluna":col,"stage":stage,"valor":format(number,"f"),"unit":"BRL_reported"})
    return {"row_count":len(rows),"cells":cells,"columns":sorted(columns),"stages":sorted({c["stage"] for c in cells}),
            "status":"ok" if cells else "schema_review_required"}

def collect(now,getter=get):
    year,period,end=latest_due(now.date())
    params={"an_exercicio":year,"nr_periodo":period,"co_tipo_demonstrativo":"RREO","no_anexo":ANEXO,"co_esfera":"U","id_ente":1}
    report={"generated_at":now.isoformat(),"source_url":URL,"query_params":params,"period_end":end.isoformat(),"entity":"União",
            "publication_authorized":False,"limitations":["Reported cells, not independent proof of spending or outcomes",
                "No summation of overlapping totals, accounts, subtotals or intra-budget flows",
                "Restos a pagar are not automatically included","A missing cell is not zero","No cross-period comparison"]}
    try:
        raw=getter(URL,params)
        report.update(parse(raw,year,period),response_sha256=hashlib.sha256(raw).hexdigest())
    except Exception as exc:
        report.update(status="unavailable",error_type=type(exc).__name__)
        if isinstance(exc,ValueError) and re.fullmatch(r"[a-z_0-9]+",str(exc)):
            report["error_code"]=str(exc)
        # Record schema shape, not unvalidated values, for diagnosis.
        if "raw" in locals():
            try:
                rows=json.loads(raw).get("items",[])
                if isinstance(rows,list) and rows and isinstance(rows[0],dict):
                    report["observed_fields"]=sorted(rows[0].keys())
                    report["observed_entities"]=[dict(zip(("cod_ibge","instituicao","esfera"),v)) for v in sorted({tuple(str(r.get(k,""))[:120] for k in ("cod_ibge","instituicao","esfera")) for r in rows if isinstance(r,dict)})][:10]
                    report["observed_columns"]=sorted({r.get("coluna") for r in rows if isinstance(r,dict) and isinstance(r.get("coluna"),str)})[:40]
            except Exception:
                pass
    return report

def main():
    report=collect(now_local())
    save("data/budget_context.json",report)
    print(json.dumps({k:report[k] for k in ("status","query_params","row_count","stages","error_type","error_code","observed_fields") if k in report},ensure_ascii=False))
if __name__=="__main__":
    main()
