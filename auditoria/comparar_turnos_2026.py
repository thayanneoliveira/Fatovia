"""FATOVIA AUDITA 2026: comparação oficial do primeiro e segundo turnos.

Chave UF / código TSE município / zona / seção.
1º turno: BWeb+CEFT do TSE com hash SHA512 publicado.
2º turno: evidência por seção do FatoVia (40877055121), verificada por SHA512.

Métricas não identificam indivíduos, nem associam identificação biométrica a
voto. Diferenças entre turnos são achados descritivos, NÃO fraude.
"""
from __future__ import annotations
import argparse,csv,gzip,json,math,statistics
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
from tempfile import TemporaryDirectory

from .tse import UFS,csv_rows
from .ma_integral import checked_reference
from .proveniencia_ma import read_selected_rows

BASE="https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/"
CSV2=("uf","municipio","zona","secao","cidade","aptos_1t","aptos_2t",
"comparecimento_1t","comparecimento_2t","delta_comparecimento",
"sem_biometria_1t","sem_biometria_2t","delta_sem_biometria",
"taxa_comparecimento_1t","taxa_comparecimento_2t",
"taxa_sem_biometria_1t","taxa_sem_biometria_2t",
"delta_pp_comparecimento","delta_pp_sem_biometria",
"brancos_1t","brancos_2t","nulos_1t","nulos_2t",
"urna_1t","urna_2t","identificador_urna_diferente")
METAFIELDS=("aptos","comparecimento","sem_biometria","abstencoes","nome")
CODES=("CD_MUNICIPIO","NR_ZONA","NR_SECAO")

def key_from_row(row):
    return tuple(int(row[k]) for k in CODES)

def bweb1(path,uf):
    sec={}
    for row in csv_rows(path):
        if row.get("NR_TURNO")!="1" or row.get("CD_CARGO_PERGUNTA")!="1":
            continue
        if row["SG_UF"]!=uf:raise ValueError("UF 1T inesperada no BWeb")
        key=key_from_row(row)
        meta={
            "aptos":int(row["QT_APTOS"]),
            "comparecimento":int(row["QT_COMPARECIMENTO"]),
            "sem_biometria":int(row["QT_ELEI_BIOM_SEM_HABILITACAO"]),
            "abstencoes":int(row["QT_ABSTENCOES"]),
            "nome":row["NM_MUNICIPIO"].strip(),
        }
        entry=sec.setdefault(key,{**meta,"brancos":0,"nulos":0,"total_votos":0,"linhas":0})
        for fld in METAFIELDS:
            if entry[fld]!=meta[fld]:
                raise ValueError(f"Metadado 1T inconsistente {uf}/{key}/{fld}")
        n=int(row["QT_VOTOS"])
        if n<0:raise ValueError("Votos negativos")
        votable=int(row["NR_VOTAVEL"])
        if votable==95:entry["brancos"]+=n
        elif votable==96:entry["nulos"]+=n
        entry["total_votos"]+=n
        entry["linhas"]+=1
    if not sec:raise ValueError("Sem seções 1T presidenciais")
    errors=[]
    for key,x in sec.items():
        if (x["total_votos"]!=x["comparecimento"] or
            x["aptos"] != x["comparecimento"]+x["abstencoes"] or
            not 0<=x["sem_biometria"]<=x["comparecimento"]<=x["aptos"]):
            errors.append(key)
    if errors:
        raise ValueError(f"1T inconsistência de votos/metadados em {len(errors)} seções, amostra={errors[:6]}")
    return sec

def ceft1(path):
    sec={}
    for row in read_selected_rows(path,"ceft_"):
        k=key_from_row(row)
        if k in sec:raise ValueError(f"CEFT1T duplicado {k}")
        sec[k]=row.get("NR_URNA_EFETIVADA","")
    return sec

def read_2t(path,uf):
    d={}
    with gzip.open(path,"rt",newline="",encoding="utf-8") as fp:
        for row in csv.DictReader(fp):
            if row["uf"]!=uf:raise ValueError("UF 2T diferente")
            key=tuple(int(row[k]) for k in ("cod_municipio_tse","zona","secao"))
            if key in d:raise ValueError("Duplicata 2T")
            d[key]=row
    return d

def rate(num,den):
    return num/den if den else None

def roundf(x):
    return round(float(x),8) if x is not None else None

def run_uf(uf,dir2,outdir):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    result={"uf":uf,"ano":2026,"gerado_utc":datetime.now(timezone.utc).isoformat(),
        "escopo":"Comparação 1º e 2º turno 2026 por seção eleitoral, presidencial",
        "status":"INCONCLUSIVO","fontes":{},"cobertura":{},"indicadores":{},"municipios":[],"limitacoes":[
            "Diferenças entre turnos não são automaticamente irregularidades ou substituições indevidas.",
            "Dados agregados não identificam votos individuais, eleitores ou relação causal entre urna e resultado.",
            "Quando uma seção não aparece em um dos turnos, ela não é imputada nem tratada como zero.",
            "Identificador físico diferente entre turnos não indica, por si, ocorrência de contingência.",
            "Os totais de habilitação sem biometria são campos agregados e não significam votos irregulares.",
        ]}
    try:
        hist=Path(dir2)/(uf+".json")
        path2=Path(dir2)/(uf+".csv.gz")
        if not path2.is_file() or not hist.is_file():raise ValueError("Baseline 2º turno ausente")
        second_meta=json.loads(hist.read_text(encoding="utf-8"))
        if second_meta["status"] not in ("OK","ALERTAS_DE_COBERTURA"):
            raise ValueError("Baseline 2T inconclusivo")
        second=read_2t(path2,uf)
        if len(second)!=second_meta["contagens"]["secoes_bu"]:
            raise ValueError("Quantidade de seções 2T diferente do baseline")
        url_bu=BASE+f"buweb/bweb_1t_{uf}_051020261403.zip"
        url_ceft=BASE+f"correspefet/CEFT_1t_{uf}_051020261049.zip"
        with TemporaryDirectory(prefix=f"fatovia-turnos-{uf}-") as tmp:
            bu_path,bu_meta=checked_reference(url_bu,"bu1.zip",tmp)
            ceft_path,ceft_meta=checked_reference(url_ceft,"ceft1.zip",tmp)
            first=bweb1(bu_path,uf)
            ceft=ceft1(ceft_path)
            result["fontes"]={
                "bweb_1t":{"url":url_bu,"sha512":bu_meta["sha512"],"bytes":bu_meta["bytes"]},
                "ceft_1t":{"url":url_ceft,"sha512":ceft_meta["sha512"],"bytes":ceft_meta["bytes"]},
                "bweb_2t":{"url":second_meta["fontes"]["BU"]["url"],
                           "sha512":second_meta["fontes"]["BU"]["sha512"]},
                "ceft_2t":{"url":second_meta["fontes"]["CEFT"]["url"],
                           "sha512":second_meta["fontes"]["CEFT"]["sha512"]},
            }
        shared=set(first)&set(second)
        result["cobertura"]={
            "secoes_1t":len(first),"secoes_2t":len(second),
            "secoes_em_ambos":len(shared),
            "apenas_1t":len(set(first)-set(second)),
            "apenas_2t":len(set(second)-set(first)),
            "ceft_1t":len(ceft),
            "secao_1t_sem_ceft":len(set(first)-set(ceft)),
            "amostra_apenas_1t":[list(k) for k in sorted(set(first)-set(second))[:20]],
            "amostra_apenas_2t":[list(k) for k in sorted(set(second)-set(first))[:20]],
        }
        summary=Counter()
        bycity=defaultdict(Counter)
        differences=[]
        with gzip.open(outdir/(uf+".csv.gz"),"wt",encoding="utf-8",newline="") as f:
            wr=csv.DictWriter(f,fieldnames=CSV2)
            wr.writeheader()
            for k in sorted(shared):
                x,y=first[k],second[k]
                a1,a2=x["aptos"],int(y["aptos"])
                t1,t2=x["comparecimento"],int(y["comparecimento"])
                b1,b2=x["sem_biometria"],int(y["sem_biometria"])
                v1,v2=x["brancos"],int(y["brancos"])
                n1,n2=x["nulos"],int(y["nulos"])
                m1=rate(b1,t1);m2=rate(b2,t2)
                c1=rate(t1,a1);c2=rate(t2,a2)
                delta_m=(m2-m1)*100 if m1 is not None and m2 is not None else None
                delta_c=(c2-c1)*100 if c1 is not None and c2 is not None else None
                urna1=ceft.get(k,"")
                urna2=y["urna_efetivada"]
                changed=int(bool(urna1 and urna2 and urna1!=urna2))
                row={
                    "uf":uf,"municipio":k[0],"zona":k[1],"secao":k[2],
                    "cidade":y["nome_municipio"],
                    "aptos_1t":a1,"aptos_2t":a2,
                    "comparecimento_1t":t1,"comparecimento_2t":t2,
                    "delta_comparecimento":t2-t1,
                    "sem_biometria_1t":b1,"sem_biometria_2t":b2,
                    "delta_sem_biometria":b2-b1,
                    "taxa_comparecimento_1t":roundf(c1),
                    "taxa_comparecimento_2t":roundf(c2),
                    "taxa_sem_biometria_1t":roundf(m1),
                    "taxa_sem_biometria_2t":roundf(m2),
                    "delta_pp_comparecimento":roundf(delta_c),
                    "delta_pp_sem_biometria":roundf(delta_m),
                    "brancos_1t":v1,"brancos_2t":v2,
                    "nulos_1t":n1,"nulos_2t":n2,
                    "urna_1t":urna1,"urna_2t":urna2,
                    "identificador_urna_diferente":changed,
                }
                wr.writerow(row)
                for scope in (summary,bycity[(k[0],y["nome_municipio"])]):
                    scope["secoes"]+=1
                    scope["comparecimento_1t"]+=t1
                    scope["comparecimento_2t"]+=t2
                    scope["aptos_1t"]+=a1
                    scope["aptos_2t"]+=a2
                    scope["sem_biometria_1t"]+=b1
                    scope["sem_biometria_2t"]+=b2
                    scope["brancos_1t"]+=v1
                    scope["brancos_2t"]+=v2
                    scope["nulos_1t"]+=n1
                    scope["nulos_2t"]+=n2
                    scope["urna_diferente"]+=changed
                    if delta_m is not None:scope["delta_pp_biometria_sum"]+=delta_m
                    if delta_c is not None:scope["delta_pp_comparecimento_sum"]+=delta_c
                if delta_c is not None and delta_m is not None:
                    differences.append({"municipio":y["nome_municipio"],"municipio_tse":k[0],
                        "zona":k[1],"secao":k[2],
                        "delta_pp_comparecimento":roundf(delta_c),
                        "delta_pp_sem_biometria":roundf(delta_m),
                        "aptos_1t":a1,"aptos_2t":a2})
        summary["secoes_com_equipamento_comparavel"]=sum(
            bool(ceft.get(k,"") and second[k]["urna_efetivada"]) for k in shared)
        cities=[]
        for (code,city),c in sorted(bycity.items()):
            v={**c,"cod_municipio_tse":code,"nome_municipio":city}
            c1=rate(c["comparecimento_1t"],c["aptos_1t"])
            c2=rate(c["comparecimento_2t"],c["aptos_2t"])
            m1=rate(c["sem_biometria_1t"],c["comparecimento_1t"])
            m2=rate(c["sem_biometria_2t"],c["comparecimento_2t"])
            v.update({"taxa_comparecimento_1t":roundf(c1),
                "taxa_comparecimento_2t":roundf(c2),
                "delta_pp_comparecimento":roundf(100*(c2-c1)) if c1 is not None and c2 is not None else None,
                "taxa_biometria_1t":roundf(m1),
                "taxa_biometria_2t":roundf(m2),
                "delta_pp_biometria":roundf(100*(m2-m1)) if m1 is not None and m2 is not None else None})
            cities.append(v)
        c1=rate(summary["comparecimento_1t"],summary["aptos_1t"])
        c2=rate(summary["comparecimento_2t"],summary["aptos_2t"])
        m1=rate(summary["sem_biometria_1t"],summary["comparecimento_1t"])
        m2=rate(summary["sem_biometria_2t"],summary["comparecimento_2t"])
        result["indicadores"]={**dict(summary),
            "taxa_comparecimento_1t":roundf(c1),
            "taxa_comparecimento_2t":roundf(c2),
            "delta_pp_comparecimento":roundf(100*(c2-c1)) if c1 is not None and c2 is not None else None,
            "taxa_sem_biometria_1t":roundf(m1),
            "taxa_sem_biometria_2t":roundf(m2),
            "delta_pp_sem_biometria":roundf(100*(m2-m1)) if m1 is not None and m2 is not None else None}
        result["municipios"]=cities
        result["status"]="OK"
    except Exception as exc:
        result["status"]="INCONCLUSIVO"
        result["erro"]=f"{type(exc).__name__}: {exc}"
        (outdir/(uf+".csv.gz")).unlink(missing_ok=True)
    (outdir/(uf+".json")).write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"uf":uf,"status":result["status"],"cobertura":result["cobertura"],
         "indicadores":result["indicadores"],"erro":result.get("erro")},ensure_ascii=False),flush=True)
    return result["status"]=="OK"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--uf",required=True,choices=UFS)
    p.add_argument("--baseline-2t",default="work/geografia2t")
    p.add_argument("--out",default="work/comparacao-turnos")
    a=p.parse_args()
    if not run_uf(a.uf,a.baseline_2t,a.out):
        raise SystemExit(2)

if __name__=="__main__":
    main()
