"""Claim/evidence ledger for the approved documentary template only.

Free-form draft claims are not approved by this module. An exact excerpt is
evidence of what a source says, never proof that its contents are true.
"""
import hashlib
import json
from .render import cards_for
from .evidence import source_ok

POLICY="documentary-claims-v1"

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def build(item):
    if not source_ok(item):
        raise ValueError("source_identifier_mismatch")
    cards=cards_for(item)
    if len(cards)!=7:
        raise ValueError("unexpected_template")
    summary=item["summary"].strip()
    source=item["source_url"]
    entries=[]
    def add(loc,text,kind,field=None,excerpt=None,limit=None):
        row={"location":loc,"text":text,"type":kind,"limitation":limit}
        if field:
            original=item[field]
            if not isinstance(original,str) or not excerpt or excerpt not in original:
                raise ValueError("excerpt_not_in_source")
            offset=original.index(excerpt)
            row["evidence"]={"url":source,"field":field,"excerpt":excerpt,
                "start":offset,"end":offset+len(excerpt),"field_sha256":digest(original)}
        else:
            row["evidence"]=None
        entries.append(row)
    add("card_01",item["title"],"document_identity","title",item["title"],"Identifica a proposição, não sua aprovação.")
    first=cards[1][1]
    add("card_02",first,"attributed_excerpt","summary",first,"Ementa oficial, não texto integral nem prova de impacto.")
    second=cards[2][1]
    if summary!=first:
        if (first+" "+second).strip()!=summary:
            raise ValueError("summary_coverage_missing")
        add("card_03",second,"attributed_excerpt","summary",second,"Continuação da ementa oficial.")
    else:
        add("card_03",second,"template_explanation",limit="Não acrescenta fatos externos.")
    if len(item["stage"])>340:
        raise ValueError("stage_truncated_context")
    add("card_04",item["stage"],"procedural_record","stage",item["stage"],"Registro de tramitação na data de referência.")
    add("card_04",item["stage_date"],"record_date","stage_date",item["stage_date"],"Data do andamento, não da vigência.")
    add("card_05",cards[4][1],"scope_limitation",limit="Não atribui impacto, vigência ou financiamento.")
    add("card_06",cards[5][1],"open_questions",limit="Questões para acompanhamento, não afirmações comprovadas.")
    add("card_07",item["title"],"source_reference","title",item["title"],"Referência documental.")
    # Caption must be independently reconstructed and checked by editorial_audit.
    add("caption",item["title"],"document_identity","title",item["title"],"Identifica a proposição.")
    add("caption",item["stage_date"],"record_date","stage_date",item["stage_date"],"Data registrada na fonte.")
    return {"policy":POLICY,"document_id":item["id"],"version":item["version"],
            "source_url":source,"entries":entries,
            "unverified_dimensions":["legal_effect","implementation","budget","causality","social_impact"],
            "limitation":"Mapeamento do modelo fixo; não valida narrativa livre, nem o conteúdo substantivo da ementa."}

def draft_matrix(output,document):
    """Unverified free-text questions stay unresolved even when a regex check passes."""
    if not isinstance(output,dict):
        return []
    summary=document.get("summary","")
    quote=output.get("citacao")
    rows=[]
    for field,value in [("titulo",output.get("titulo"))]+[(f"perguntas[{i}]",q) for i,q in enumerate(output.get("perguntas",[]) if isinstance(output.get("perguntas"),list) else [])]:
        rows.append({"location":field,"text":value,"type":"unverified_draft","decision":"requires_semantic_review","evidence":None})
    exact=isinstance(quote,str) and bool(quote.strip()) and isinstance(summary,str) and quote in summary
    rows.append({"location":"citacao","text":quote,"type":"attributed_excerpt",
        "decision":"literal_match_only" if exact else "unverified",
        "evidence":{"url":document.get("source_url"),"field":"summary","excerpt":quote,"start":summary.index(quote),"end":summary.index(quote)+len(quote)} if exact else None})
    return rows
