"""FatoVia audiovisual director V1: deterministic planning, not LLM semantic reasoning.
All plans are laboratory candidates; never publish or invent timings."""
import argparse, hashlib, json, math, re, unicodedata
from pathlib import Path

ASSETS={
 "home":"casa / ambiente familiar","person":"pessoa / personagem recorrente",
 "construction":"obra / construção","school":"escola / creche","health":"unidade de saúde",
 "money":"dinheiro / orçamento","transport":"veículo / logística","institution":"instituição pública",
 "document":"documento / portal ilustrativo","clock":"relógio / passagem do tempo",
 "comparison":"comparação sem números inventados","question":"interrogação",
 "food":"alimentos / supermercado","job":"trabalho / renda","abstract":"revisão visual necessária"}
# Order breaks ties only. Keywords are clues, not proof of meaning or factual claims.
RULES=[
 ("inspection","document",r"fiscaliz\w*|transparencia|consult\w*|document\w*|investig\w*|painel|contrato|verific\w*","inspect"),
 ("time","clock",r"meses|anos|tempo|prazo|cresce|atras\w*|espera","progress"),
 ("construction","construction",r"obra[s]?|constru\w*|terreno|tijolo|materia(?:l|is)|trabalhadores","assemble"),
 ("school","school",r"creche|escola|crianca[s]?|aluno[s]?|professor\w*","reveal"),
 ("health","health",r"hospital|medico[s]?|saude|paciente[s]?|consulta[s]?|fila[s]?","reveal"),
 ("finance","money",r"dinheiro|orcamento|recurso[s]?|renda|salario|preco[s]?|imposto[s]?|custo[s]?|juros","compare"),
 ("work","job",r"trabalh\w*|emprego[s]?|empresa[s]?","reveal"),
 ("food","food",r"supermercado|comida|alimento[s]?|arroz|feijao|carrinho","reveal"),
 ("transport","transport",r"estrada[s]?|transporte[s]?|onibus|caminhao|frete","flow"),
 ("public","institution",r"prefeitura|govern\w*|congresso|municipio|politico[s]?|cidade","reveal"),
 ("home","home",r"casa|familia|moradia|lar","reveal"),
 ("person","person",r"pedro|maria|mae|pai|pessoa[s]?|cidada\w*","reveal"),
]
def norm(s):
    return "".join(c for c in unicodedata.normalize("NFD",s.casefold()) if unicodedata.category(c)!="Mn")
def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
def require(condition,msg):
    if not condition: raise ValueError(msg)
def choose(text, tags=None):
    clean=norm(text)
    hits=[]
    for name,asset,pattern,motion in RULES:
        count=len(re.findall(r"\b(?:"+pattern+r")\b",clean))
        if count: hits.append((count,name,asset,motion))
    hits.sort(key=lambda x:-x[0])
    if tags:
        require(isinstance(tags,list) and all(x in ASSETS and x!="abstract" for x in tags),"unknown authored asset")
        assets=list(dict.fromkeys(tags))
        return {"template":"authored","assets":assets,"motion":"reveal","basis":"editor_authored","confidence":"requires_semantic_review"}
    if not hits:
        return {"template":"unresolved","assets":["question" if "?" in text else "abstract"],"motion":"hold","basis":"no_specific_match","confidence":"low"}
    first=hits[0]
    assets=list(dict.fromkeys(r[2] for r in hits))[:3]
    if "?" in text and len(assets)<3: assets.append("question")
    return {"template":first[1],"assets":assets,"motion":first[3],"basis":"keyword_heuristic","confidence":"requires_semantic_review"}

def create_plan(rows, manifest, audit):
    require(isinstance(rows,list) and bool(rows),"empty script")
    duration=float(manifest["duration"])
    require(math.isfinite(duration) and duration>0,"invalid duration")
    require(manifest["phrases"]==len(rows) and audit["phrase_count"]==len(rows),"phrase count mismatch")
    require(audit["audio_sha256"]==manifest["sha256_mp3"],"audio identity mismatch")
    require(abs(float(audit["duration"])-duration)<=.05,"duration mismatch")
    blocks=manifest["blocks"];cursor=1;previous_end=0.
    for b in blocks:
        f,l=b["phrase_first"],b["phrase_last"]
        require(f==cursor and f<=l<=len(rows),"block coverage")
        expect=" ".join(x.get("spoken",x["caption"]) for x in rows[f-1:l])
        require(expect==b["spoken"],"script mismatch")
        s,e=float(b["start"]),float(b["end"])
        require(0<=s<e<=duration+.005 and s>=previous_end-.005,"invalid block interval")
        previous_end=e;cursor=l+1
    require(cursor==len(rows)+1 and abs(previous_end-duration)<=.05 and abs(float(blocks[0]["start"]))<=.005,"incomplete timing")
    cues={}
    for c in audit["candidate_cues"]:
        k=c["phrase"]
        require(type(k)==int and 1<=k<=len(rows) and k not in cues,"invalid cue id")
        require(c["caption"]==rows[k-1]["caption"],"caption identity mismatch")
        s,e=float(c["start"]),float(c["end"])
        require(0<=s<e<=duration+.05,"invalid cue time")
        cues[k]=c
    scenes=[]
    for j,b in enumerate(blocks):
        f,l=b["phrase_first"],b["phrase_last"];indexes=list(range(f,l+1))
        start=float(b["start"]);stop=float(blocks[j+1]["start"]) if j+1<len(blocks) else duration
        safe=all(k in cues for k in indexes)
        if safe:
            last=start
            for k in indexes:
                c=cues[k]
                if float(c["start"])<last-.02 or float(c["end"])>float(b["end"])+.05: safe=False;break
                last=float(c["end"])
        if safe:
            spans=[([k],start if n==0 else float(cues[k]["start"]),float(cues[indexes[n+1]]["start"]) if n+1<len(indexes) else stop,"asr_estimated") for n,k in enumerate(indexes)]
            if any(e<=s for _,s,e,_ in spans): safe=False
        if not safe:
            spans=[(indexes,start,stop,"original_block_only")]
        for ids,s,e,timing in spans:
            content=" ".join(rows[k-1]["caption"] for k in ids)
            tags=list(dict.fromkeys(tag for k in ids for tag in rows[k-1].get("visual_tags",[])))
            selection=choose(content,tags or None)
            # Preserve actual named character references, no fabricated identities.
            continuity=[name for name in ("Pedro","Maria") if re.search(r"\b"+name+r"\b",content)]
            scenes.append({"id":len(scenes)+1,"phrase_ids":ids,"start":s,"end":e,"timing":timing,"spoken_content":content,"continuity":continuity,**selection,"motion_window":[0.1,0.85],"visual_claims_added":[],"review_required":True})
    require([k for s in scenes for k in s["phrase_ids"]]==list(range(1,len(rows)+1)),"lost phrases")
    require(all(abs(a["end"]-b["start"])<.001 for a,b in zip(scenes,scenes[1:])),"scene gap")
    return {"version":"director-v1-lab","status":"review_only","publish_allowed":False,"script_sha256":digest(rows),"audio_sha256":manifest["sha256_mp3"],"duration":duration,"audit_status":audit["status"],"scene_count":len(scenes),"block_fallback_scenes":sum(s["timing"]=="original_block_only" for s in scenes),"unresolved_scenes":sum(s["template"]=="unresolved" for s in scenes),"asset_registry":ASSETS,"limitations":"Keyword rules or authored tags; no semantic guarantee. Timings from audit estimates or original block boundaries. No visual claims, no automatic publication.","scenes":scenes}

def main():
    p=argparse.ArgumentParser();p.add_argument("--script",type=Path,required=True);p.add_argument("--manifest",type=Path,required=True);p.add_argument("--audit",type=Path,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    plan=create_plan(*[json.loads(x.read_text(encoding="utf-8")) for x in (a.script,a.manifest,a.audit)])
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in plan.items() if k not in ("scenes","asset_registry")},ensure_ascii=False))
if __name__=="__main__":main()
