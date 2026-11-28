"""Documentary evidence gate: proves traceability, not truth of claims in a bill."""
import hashlib
import json
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse


def projection(item):
    result={k:item.get(k) for k in ("id","version","title","summary","stage","stage_date","source_url","public_url","caption","cards")}
    if str(item.get("id","")).startswith("civic:"):result["observation"]=item.get("observation")
    return result


def fingerprint(item):
    return hashlib.sha256(json.dumps(projection(item),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def source_ok(item):
    if str(item.get("id","")).startswith("civic:"):
        from .civic import valid
        return valid(item)
    m = re.fullmatch(r"camara:([0-9]+)", str(item.get("id","")))
    if not m:
        return False
    ident=m.group(1)
    return (item.get("source_url")==f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{ident}"
            and item.get("public_url")==f"https://www.camara.leg.br/propostas-legislativas/{ident}"
            and bool(re.fullmatch(r"(?:PL|PLP|PEC|PDL) [0-9]+/[0-9]{4}",str(item.get("title","")))))


def seal(item, now):
    if not source_ok(item):
        raise ValueError("source_identifier_mismatch")
    civic=str(item.get("id","")).startswith("civic:")
    item["evidence"] = {
        "schema":1,"kind":"official_series_observation" if civic else "official_document_attribution","checked_at":now.isoformat(),
        "source":item["source_url"],"record_date":item["stage_date"],"content_sha256":fingerprint(item),
        "claims":[{"field":"title","basis":"identificacao_da_proposicao"},
                  {"field":"summary","basis":"ementa_oficial_atribuida"},
                  {"field":"stage","basis":"registro_de_tramitacao"}],
        "limitations":"Não confirma veracidade das alegações do projeto, aprovação, execução ou impacto."
    }
    if civic:
        item["evidence"]["claims"]=[{"field":"observation","basis":"official_series"}]
        item["evidence"]["limitations"]="Não comprova causalidade nem impacto individual."
    return item


def sealed(item, now):
    evidence=item.get("evidence")
    if not isinstance(evidence,dict) or not source_ok(item):
        return False
    try:
        checked=datetime.fromisoformat(evidence["checked_at"])
        stage=datetime.fromisoformat(item["stage_date"]).date()
        return (evidence["schema"]==1 and evidence["kind"]==("official_series_observation" if str(item.get("id","")).startswith("civic:") else "official_document_attribution")
                and evidence["source"]==item["source_url"] and evidence["record_date"]==item["stage_date"]
                and checked<=now
                and stage<=now.date()
                and evidence["content_sha256"]==fingerprint(item))
    except (KeyError,TypeError,ValueError):
        return False


def read_document(root,fetcher,errors=None):
    # Use the official detail response for identity, text and current status.
    detail=fetcher(root).get("dados")
    if not isinstance(detail,dict):
        raise ValueError("invalid_detail")
    stage=detail.get("statusProposicao")
    if isinstance(stage,dict) and stage.get("dataHora") and (stage.get("descricaoTramitacao") or stage.get("despacho") or stage.get("siglaOrgao")):
        return detail,stage,"detail_status"
    # Fallback: no unsupported sorting parameter. Select latest timestamp locally.
    history=fetcher(root+"/tramitacoes",{"ordem":"DESC","itens":100})
    rows=history.get("dados")
    if not isinstance(rows,list) or not rows:
        return detail,None,"missing"
    rows=[r for r in rows if isinstance(r,dict) and r.get("dataHora")]
    if not rows:
        return detail,None,"missing"
    # A paginated history cannot prove latest record unless the API confirms order.
    if any(link.get("rel")=="next" for link in history.get("links",[]) if isinstance(link,dict)):
        return detail,None,"incomplete"
    return detail,max(rows,key=lambda r:r["dataHora"]),"history"


def verify_live(item, fetcher=None):
    if str(item.get("id","")).startswith("civic:"):
        from .civic import verify
        from .engine import now_local
        return verify(item,now_local(),fetcher) if fetcher is not None else verify(item,now_local())
    # Do not follow arbitrary supplied links or redirects; the source ID is bound above.
    if not source_ok(item):
        return False
    if fetcher is None:
        import requests
        def fetcher(url,params=None):
            response=requests.get(url,params=params,timeout=(5,15),allow_redirects=False,
                                  headers={"Accept":"application/json","User-Agent":"FatoVia-Audit/1.0"})
            if response.status_code!=200:
                raise ValueError("source unavailable")
            return response.json()
    from .engine import from_camara
    try:
        root=item["source_url"]
        detail,stage,_=read_document(root,fetcher)
        if not stage:
            return False
        fresh=from_camara(detail,stage)
        return all(fresh.get(k)==item.get(k) for k in ("id","version","title","summary","stage","stage_date","source_url","public_url"))
    except Exception:
        return False
