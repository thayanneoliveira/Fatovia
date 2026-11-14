"""Evidence-linked descriptive dossiers. Never authorizes publication."""
from datetime import datetime,timedelta
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP
import re
from .engine import load,save,now_local
from .claim_matrix import digest

def recent(report,now):
    try:
        stamp=datetime.fromisoformat(report["generated_at"])
        return now-timedelta(days=3)<=stamp<=now
    except (KeyError,TypeError,ValueError):
        return False

def decimal(value):
    if not isinstance(value,str) or not re.fullmatch(r"-?\d+(?:\.\d+)?",value):
        raise ValueError("invalid_decimal")
    n=Decimal(value)
    if not n.is_finite():
        raise ValueError("invalid_number")
    return n

def series_entry(report,key,now):
    if not recent(report,now):
        return None
    row=report.get("series",{}).get(key,{})
    if row.get("status")!="ok" or not re.fullmatch(r"[a-f0-9]{64}",row.get("response_sha256","")):
        return None
    values=row.get("observations",[])
    if not values:
        return None
    return row

def observation(row,period=None):
    values=[v for v in row["observations"] if period is None or v["period"]==period]
    if not values:
        return None
    v=values[-1]
    decimal(v["value"])
    return {"metric":row.get("label",row.get("name")),"period":v["period"],"value":v["value"],
            "unit":row["unit"],"frequency":row["frequency"],"source_url":row["source_url"],
            "query_params":row.get("query_params",{}),"response_sha256":row["response_sha256"],
            "limitation":row["limitation"]}

def dossier(name,question,evidence,gaps):
    body={"id":name,"question":question,"evidence":evidence,"unresolved":gaps,
          "decision":"research_only","publication_authorized":False}
    body["dossier_sha256"]=digest(body)
    return body

def budget_evidence(report,now):
    if not recent(report,now) or report.get("status")!="ok" or report.get("entity")!="União":
        return []
    if not re.fullmatch(r"[a-f0-9]{64}",report.get("response_sha256","")):
        return []
    rows=[r for r in report.get("cells",[]) if r.get("cod_conta")=="DespesasExcetoIntraOrcamentarias" and r.get("rotulo")=="Padrão"]
    stages={}
    for r in rows:
        stage=r["stage"]
        if stage in stages or r.get("unit")!="BRL_reported":
            return []
        stages[stage]=r
    required=("dotacao_atualizada","empenhado","liquidado","pago")
    if not all(s in stages for s in required):
        return []
    amounts={s:decimal(stages[s]["valor"]) for s in required}
    if not amounts["dotacao_atualizada"]>0 or any(v<0 for v in amounts.values()):
        return []
    common={"period_end":report["period_end"],"source_url":report["source_url"],
            "query_params":report["query_params"],"response_sha256":report["response_sha256"],
            "account_code":"DespesasExcetoIntraOrcamentarias","scope":"União, despesas exceto intra-orçamentárias"}
    result=[{**common,"stage":s,"value":stages[s]["valor"],"unit":"BRL_reported","column":stages[s]["coluna"]} for s in required]
    # A ratio describes reported budget execution, not physical delivery.
    result.append({**common,"metric":"pagamentos / dotação atualizada","value":str((amounts["pago"]/amounts["dotacao_atualizada"]*100).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)),
                   "unit":"%","formula":"100 * pago / dotacao_atualizada","inputs":{"pago":stages["pago"]["valor"],"dotacao_atualizada":stages["dotacao_atualizada"]["valor"]}})
    return result

def build(bcb,ibge,budget,now):
    cases=[]
    full=series_entry(ibge,"ipca_monthly",now); core=series_entry(bcb,"16122",now)
    if full and core:
        common=set(v["period"] for v in full["observations"])&set(v["period"] for v in core["observations"])
        if common:
            period=max(common)
            cases.append(dossier("inflacao_medidas","Por que IPCA cheio e núcleo de inflação são medidas diferentes?",
                [observation(full,period),observation(core,period)],["Composição dos índices","Sem conclusão sobre causas ou inflação individual"]))
    selic=series_entry(bcb,"432",now)
    if selic:
        cases.append(dossier("juros_contexto","O que a meta Selic mede e o que ela não mede?",
            [observation(selic)],["Taxas de crédito efetivas","Transmissão monetária","Sem inferência de impacto individual"]))
    unemp=series_entry(ibge,"unemployment_quarterly",now)
    if unemp:
        vals=unemp["observations"]
        # Compare only the same quarter in different years; no seasonal adjustment claimed.
        period=vals[-1]["period"]
        prev=f"{int(period[:4])-1:04d}{period[4:]}"
        a=observation(unemp,prev); z=observation(unemp,period)
        if a and z:
            delta=decimal(z["value"])-decimal(a["value"])
            cases.append(dossier("desocupacao_periodos","Como mudou a taxa de desocupação em relação ao mesmo trimestre anterior?",
                [a,z,{"metric":"diferença em pontos percentuais","value":str(delta),"unit":"p.p.","formula":"taxa atual - taxa do mesmo trimestre do ano anterior"}],
                ["Margens de erro","Composição da força de trabalho","Sem atribuição a uma política específica"]))
    evidence=budget_evidence(budget,now)
    if evidence:
        cases.append(dossier("execucao_orcamentaria","Qual a diferença entre dotação, empenho, liquidação e pagamento na União?",
            evidence,["Não mede resultados sociais","Não agrega restos a pagar","Não permite concluir desempenho de um programa específico"]))
    return {"generated_at":now.isoformat(),"dossiers":cases,"publication_authorized":False,
            "limitations":"Descriptive context; no cross-source causal conclusions. Dossiers require editorial review."}

def main():
    report=build(load("data/economic_context.json"),load("data/ibge_context.json"),load("data/budget_context.json"),now_local())
    save("data/investigation_report.json",report)
    print("DOSSIERS",len(report["dossiers"]),[x["id"] for x in report["dossiers"]])
if __name__=="__main__":
    main()
