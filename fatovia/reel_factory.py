"""V6 documentary Reel planner. Only already reviewed official documents; never posts."""
import argparse, hashlib, json, re
from pathlib import Path
from .engine import load, save, now_local
from .editorial_audit import approved
from .evidence import verify_live
from .didactic import reviewed

TAGS={
 "economia":["Economia","Impostos","EconomiaBrasileira"],
 "saude":["SaudePublica","SUS","DireitoASaude"],
 "educacao":["Educacao","Escola","PoliticasEducacionais"],
 "seguranca":["SegurancaPublica","Direitos","Cidadania"],
 "ambiente":["MeioAmbiente","Sustentabilidade","PoliticaAmbiental"],
 "tecnologia":["Tecnologia","Inovacao","DireitosDigitais"],
 "infraestrutura":["Infraestrutura","Mobilidade","ServicosPublicos"],
}
SHOTS=["human_hook","context_detail","street","document","document_detail","mechanism","mechanism_detail","people","tradeoff","comparison","questions","reflection"]
def digest(s):
    return hashlib.sha256(s.encode()).hexdigest()
def caption(plan):
    qs=plan["questions"]
    tags=list(dict.fromkeys(["FatoVia",*TAGS[plan["topic"]],"PoliticasPublicas"]))[:5]
    text="\n\n".join([plan["hook"],plan["proposal"]+" "+plan["conditional"],
        "\n".join(qs)+"\nConta nos comentários qual ponto você considera mais importante e por quê.",
        "Proposta em discussão; não é uma mudança já confirmada. Fonte oficial: "+plan["source"]["public_url"],
        "ID editorial: "+plan["id"]+"/"+plan["version"]," ".join("#"+t for t in tags)])
    if not 50<=len(text)<=2200 or len(re.findall(r"(?<!\w)#[\w]+",text))>5:raise ValueError("caption invalid")
    return text
def build_plan(item, review):
    cards=review["cards"]
    if len(cards)!=5 or tuple(c["kind"] for c in cards)!=("question","proposal","mechanism","conditional","questions"):raise ValueError("review missing")
    topic=next((x for x in item["topics"] if x in TAGS),None)
    if not topic:raise ValueError("no thematic art profile")
    qs=[s.strip()+"?" for s in cards[4]["body"].split("?")[:-1] if s.strip()]
    if len(qs)<2:qs+=["Que informação ainda falta para avaliar essa proposta?","Como verificar seus possíveis efeitos na prática?"]
    qs=qs[:2]
    hook=cards[0]["headline"]
    if not hook.endswith("?"):hook=hook.rstrip(".")+"?"
    proposal=cards[1]["body"]; conditional=cards[3]["body"]
    blocks=[hook,cards[0]["body"],"Existe uma proposta em discussão.",
        "Na Câmara dos Deputados, o projeto trata deste tema.",proposal,
        cards[2]["headline"],cards[2]["body"],"Mas uma proposta não é uma mudança já confirmada.",
        conditional,"Os efeitos dependem do texto final e da forma de implementação.",qs[0],qs[1]]
    script="\n".join(blocks)+"\n"
    if not 45<=len(script.split())<=250:raise ValueError("script length")
    seed=digest(item["id"]+"/"+item["version"])
    plan={"schema":1,"id":"reel:"+item["id"].replace(":","-"),"version":digest(script+seed+"V6-caption2")[:14],
        "topic":topic,"seed":seed,"hook":hook,"proposal":proposal,"conditional":conditional,
        "questions":qs,"source":item,"script":script,"script_sha256":digest(script),
        "shots":[{"kind":k,"line":i,"art_seed":digest(seed+k)[:16]} for i,k in enumerate(SHOTS)],
        "voice":"Algenib","visual_revision":"V6","status":"draft_requires_independent_review"}
    plan["caption"]=caption(plan)
    return plan
def select(state,now,check=approved,live=verify_live,reviewer=reviewed):
    used={x.get("id") for key in ("published","reel_pending","withdrawn_publications") for x in state.get(key,[])}
    for item in sorted(state.get("pending",[]),key=lambda x:(-x.get("editorial_score",0),x["id"])):
        if item["id"] in used or "reel:"+item["id"].replace(":","-") in used:continue
        try:
            if not check(item,now) or not live(item):continue
            row=reviewer(item)
            if row:return build_plan(item,row)
        except (ValueError,TypeError,KeyError,OSError):continue
    return None
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",type=Path,required=True);args=ap.parse_args()
    plan=select(load("data/state.json"),now_local())
    if not plan:
        print("NO_REVIEWED_CANDIDATE");return
    args.out.mkdir(parents=True,exist_ok=True)
    save(args.out/"plan.json",plan)
    (args.out/"script.txt").write_text(plan["script"],encoding="utf-8")
    (args.out/"caption.txt").write_text(plan["caption"],encoding="utf-8")
    print(plan["id"],plan["version"])
if __name__=="__main__":main()
