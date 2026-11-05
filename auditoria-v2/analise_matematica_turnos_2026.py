#!/usr/bin/env python3
"""Auditoria matemática pública dos dois turnos da eleição presidencial 2026.

Consulta apenas EA20 oficial do TSE, guarda hashes e testa identidades contábeis.
Correlação ecológica é descritiva: NÃO identifica fluxo de eleitores entre opções.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv,datetime as dt,hashlib,json,math,pathlib,statistics,sys,time,urllib.request

UNITS="AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO ZZ BR".split()
ELECTIONS={1:"6257",2:"6258"}

def get(uf,turn):
    ele=ELECTIONS[turn]
    code=uf.lower()
    url=f"https://resultados.tse.jus.br/oficial/ele2026/{ele}/dados/{code}/{code}-c0001-e{int(ele):06d}-u.json"
    last=None
    for trial in range(4):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; FatoVia-public-math-audit/1.0)"})
            with urllib.request.urlopen(req,timeout=40) as response:
                raw=response.read(2_000_000)
            j=json.loads(raw)
            if str(j.get("ele")) != ele or str(j.get("t")) != str(turn):
                raise RuntimeError(f"pleito/turno incorreto: {j.get('ele')} / {j.get('t')}")
            v,e=j.get("v",{}),j.get("e",{})
            if not v or not e:raise RuntimeError("registro sem totais de votação e eleitorado")
            def i(o,k):return int(o[k])
            cand={}
            for cargo in j.get("carg",[]):
                if str(cargo.get("cd"))!="1":continue
                for ag in cargo.get("agr",[]):
                    for par in ag.get("par",[]):
                        for c in par.get("cand",[]):
                            cand[str(c.get("n"))]=int(c["vap"])
            if not {"13","22"}<=cand.keys():raise RuntimeError("votos de candidatos 13/22 não recuperáveis")
            values={"uf":uf,"turno":turn,"eleicao":ele,"sha256":hashlib.sha256(raw).hexdigest(),
                "url":url,"generated":f"{j.get('dg')} {j.get('hg')}",
                "aptos_cadastro":i(e,"te"),"aptos_instalados":i(e,"esi"),
                "comparecimento":i(e,"c"),"abstencoes":i(e,"a"),
                "validos":i(v,"vvc"),"brancos":i(v,"vb"),"nulos":i(v,"tvn"),
                "lula":cand["13"],"flavio":cand["22"],
                "outros":i(v,"vvc")-cand["13"]-cand["22"],
                "secoes_totalizadas":i(j["s"],"st")}
            if values["comparecimento"] != values["validos"]+values["brancos"]+values["nulos"]:
                raise RuntimeError("COMPARECIMENTO != VAL+BRANCO+NULO: "+uf+str(turn))
            if values["aptos_instalados"]!=values["comparecimento"]+values["abstencoes"]:
                raise RuntimeError("APTOS_INSTALADOS != COMPARECIMENTO+ABST: "+uf+str(turn))
            if values["outros"]<0:raise RuntimeError("outros negativos")
            return values
        except Exception as exc:
            last=exc
            time.sleep(1+trial)
    raise RuntimeError(f"não foi possível obter {url}: {last}")

def corr(x,y):
    if len(x)<3:return None
    a=statistics.mean(x);b=statistics.mean(y)
    n=sum((u-a)*(v-b) for u,v in zip(x,y))
    dx=sum((u-a)**2 for u in x);dy=sum((v-b)**2 for v in y)
    return round(n/math.sqrt(dx*dy),5) if dx and dy else None

def main():
    out=pathlib.Path("resultado-matematica-eleitoral")
    out.mkdir(exist_ok=True)
    data={};errors=[]
    with ThreadPoolExecutor(max_workers=8) as pool:
        tasks={pool.submit(get,uf,turn):(uf,turn) for uf in UNITS for turn in (1,2)}
        for fut in as_completed(tasks):
            uf,turn=tasks[fut]
            try:
                data[(uf,turn)]=fut.result()
                print("OK",uf,turn,flush=True)
            except Exception as ex:
                errors.append({"uf":uf,"turno":turn,"error":str(ex)})
                print("ERRO",uf,turn,str(ex),flush=True)
    report={"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "status":"INCOMPLETE","data_source":"arquivos oficiais EA20 do TSE, 1T 6257 e 2T 6258",
        "request":len(UNITS)*2,"downloads_verified":len(data),"errors":errors,
        "units":{},"country":{},"correlations":{},
        "limits":["Correlação agregada por UF é inferência ecológica e não identifica mudanças individuais de voto.",
            "Não há dados individuais de comparecimento ou óbitos.",
            "Diferenças entre comparecimento e votos válidos incluem brancos e nulos.",
            "O TSE informa 39 registros duplicados em TTE no universo cadastral de 2026.",
            "Para não misturar universos, percentuais de comparecimento usam aptos das seções instaladas."]}
    if not errors:
        rows=[]
        for uf in UNITS:
            a,b=data[(uf,1)],data[(uf,2)]
            r={"uf":uf,
              "votos_validos_1t":a["validos"],"votos_validos_2t":b["validos"],
              "comparecimento_1t":a["comparecimento"],"comparecimento_2t":b["comparecimento"],
              "delta_comparecimento":b["comparecimento"]-a["comparecimento"],
              "brancos_nulos_1t":a["brancos"]+a["nulos"],
              "brancos_nulos_2t":b["brancos"]+b["nulos"],
              "delta_invalidos":b["brancos"]+b["nulos"]-a["brancos"]-a["nulos"],
              "delta_validos":b["validos"]-a["validos"],
              "lula_1t":a["lula"],"lula_2t":b["lula"],"delta_lula":b["lula"]-a["lula"],
              "flavio_1t":a["flavio"],"flavio_2t":b["flavio"],"delta_flavio":b["flavio"]-a["flavio"],
              "outros_1t":a["outros"],
              "taxa_comparecimento_1t":round(a["comparecimento"]/a["aptos_instalados"],8),
              "taxa_comparecimento_2t":round(b["comparecimento"]/b["aptos_instalados"],8),
              "delta_taxa_comparecimento_pp":round(100*(b["comparecimento"]/b["aptos_instalados"]-a["comparecimento"]/a["aptos_instalados"]),5),
              "outros_1t_pct_validos":round(100*a["outros"]/a["validos"],5),
              "delta_participacao_lula_pp":round(100*(b["lula"]/b["validos"]-a["lula"]/a["validos"]),5),
              "delta_participacao_flavio_pp":round(100*(b["flavio"]/b["validos"]-a["flavio"]/a["validos"]),5),
              "aptos_instalados_1t":a["aptos_instalados"],"aptos_instalados_2t":b["aptos_instalados"],
              "sha256_oficial_1t":a["sha256"],"sha256_oficial_2t":b["sha256"],
              "url_oficial_1t":a["url"],"url_oficial_2t":b["url"]}
            if r["delta_validos"] != r["delta_comparecimento"] - r["delta_invalidos"]:
                errors.append({"uf":uf,"error":"identidade de comparecimento/validos/inválidos descasada"})
            if r["delta_lula"]+r["delta_flavio"] != a["outros"]+r["delta_validos"]:
                errors.append({"uf":uf,"error":"identidade dos votos dos candidatos descasada"})
            report["units"][uf]=r
            if uf!="BR":rows.append(r)
        for turn in (1,2):
            for k in ("comparecimento","abstencoes","validos","brancos","nulos","lula","flavio","outros"):
                sum_uf=sum(data[(u,turn)][k] for u in UNITS if u!="BR")
                br=data[("BR",turn)][k]
                if sum_uf!=br:errors.append({"turn":turn,"metric":k,"sum_uf":sum_uf,"br":br})
        def pairs(ax,ay):
            return corr([r[ax] for r in rows],[r[ay] for r in rows])
        report["correlations"]={
            "r_delta_turnout_rate_pp_vs_delta_lula_valid_share_pp":pairs("delta_taxa_comparecimento_pp","delta_participacao_lula_pp"),
            "r_others_share_1t_vs_delta_lula_valid_share_pp":pairs("outros_1t_pct_validos","delta_participacao_lula_pp"),
            "r_delta_turnout_rate_pp_vs_delta_flavio_valid_share_pp":pairs("delta_taxa_comparecimento_pp","delta_participacao_flavio_pp"),
            "method":"Pearson não ponderado, 28 unidades territoriais incluindo ZZ; descritivo, não causal"}
        report["country"]=report["units"]["BR"]
        report["status"]="COMPLETE_28_UNITS_MATHEMATICAL_IDENTITIES" if not errors else "INCOMPLETE"
        with (out/"comparacao_t1_t2_28_unidades.csv").open("w",encoding="utf-8",newline="") as f:
            order=[x for x in rows[0] if not x.startswith("url_")]+["url_oficial_1t","url_oficial_2t"]
            writer=csv.DictWriter(f,fieldnames=order)
            writer.writeheader();writer.writerows(rows)
    report["errors"]=errors
    (out/"manifesto_matematico_2026.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("RESULTADO",json.dumps({"status":report["status"],"errors":errors,"correlations":report["correlations"],"country":{k:v for k,v in report["country"].items() if not k.startswith(("url","sha256"))}},ensure_ascii=False),flush=True)
    raise SystemExit(0 if report["status"].startswith("COMPLETE") else 2)

if __name__=="__main__":main()
