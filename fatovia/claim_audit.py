"""Conservative independent triage for LLM drafts. NOT a semantic truth oracle."""
import re
import unicodedata

def norm(s):
    return "".join(c for c in unicodedata.normalize("NFKD",s.casefold()) if not unicodedata.combining(c))

RULES={
 "unverified_legal_status":r"\b(?:ja (?:esta em vigor|foi aprovad[oa]|virou lei|entrou em vigor)|lei aprovada|(?:governo|congresso|camara) (?:aprovou|sancionou)|beneficio garantido|passou a valer|ja vale)\b",
 "unsupported_causal_claim":r"\b(?:comprovadamente|garante|vai acabar com|vai resolver|vai reduzir|provou que|causou|responsavel por)\b",
 "loaded_presupposition":r"\b(?:por que (?:o governo|a camara|o congresso) (?:esconde|mentiu|enganou)|mais uma fraude|roubou|desviou|manipulou)\b",
 "electoral_appeal":r"\b(?:vote em|nao vote em|melhor candidato|pior candidato|apoie o partido)\b",
 "unverified_financial_promise":r"\b(?:voce vai receber|dinheiro garantido|todos receberao|desconto garantido)\b",
}

def numbers(text):
    # Numeric tokens are distinct, including decimal/percentage notation.
    return set(re.findall(r"\d+(?:[.,]\d+)*(?:\s*%)?",text))

def audit_draft(output,document):
    result={"decision":"manual_review_required","publication_authorized":False,"findings":[]}
    if not isinstance(output,dict) or not isinstance(document,dict):
        result["findings"].append({"field":"draft","code":"invalid_payload"})
        result["decision"]="rejected_by_rules"
        return result
    source=" ".join(str(document.get(k,"")) for k in ("title","summary","stage","stage_date"))
    allowed_numbers={re.sub(r"\s+","",v) for v in numbers(source)}
    fields=[("titulo",output.get("titulo"))]
    q=output.get("perguntas")
    if not isinstance(q,list):
        result["findings"].append({"field":"perguntas","code":"invalid_payload"})
        q=[]
    fields.extend((f"perguntas[{i}]",v) for i,v in enumerate(q))
    for field,value in fields:
        if not isinstance(value,str):
            result["findings"].append({"field":field,"code":"invalid_payload"})
            continue
        for code,pattern in RULES.items():
            if re.search(pattern,norm(value)):
                result["findings"].append({"field":field,"code":code})
        if any(re.sub(r"\s+","",v) not in allowed_numbers for v in numbers(value)):
            result["findings"].append({"field":field,"code":"number_not_in_source"})
    quote=output.get("citacao")
    if not isinstance(quote,str) or not quote.strip() or quote not in str(document.get("summary","")):
        result["findings"].append({"field":"citacao","code":"quote_not_exact"})
    if result["findings"]:
        result["decision"]="rejected_by_rules"
    return result
