#!/usr/bin/env python3
"""FatoVia: quatro fontes públicas por seção/zona sem dados pessoais.

BU web (2T) + Detalhe da votação (1T/2T) + ELO (1T/2T, zona)
+ Perfil do eleitorado (seção, anterior à votação). Nenhuma inferência individual.
"""
import argparse
from collections import defaultdict, Counter
import csv
import datetime as dt
import hashlib
import io
import json
import pathlib
import re
import sys
import time
import urllib.request
import zipfile

URLS = {
 "bu": "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/buweb/bweb_2t_{uf}_261020260742.zip",
 "detalhe": "https://cdn.tse.jus.br/estatistica/sead/odsele/detalhe_votacao_secao/detalhe_votacao_secao_2026.zip",
 "elo": "https://cdn.tse.jus.br/estatistica/sead/odsele/perfil_comparecimento_abstencao/perfil_comparecimento_abstencao_2026.zip",
 "perfil": "https://cdn.tse.jus.br/estatistica/sead/odsele/perfil_eleitor_secao/perfil_eleitor_secao_2026_{uf}.zip",
}
TRIPLET=("QT_APTOS","QT_COMPARECIMENTO","QT_ABSTENCOES")
PRINCIPAL=("SG_UF","CD_MUNICIPIO","NR_ZONA","NR_SECAO")

def norm(x):
    a=str(x or "").strip()
    return str(int(a)) if a.isdecimal() else a.upper()

def sha512(path):
    h=hashlib.sha512()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(2*1024*1024),b""): h.update(b)
    return h.hexdigest()

def fetch(url,path,maxsize=1300*1024**2):
    if path.exists() and path.stat().st_size>0:
        return
    ex=None
    for trial in range(3):
        part=path.with_name(path.name+".part")
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"FatoVia-coerencia-publica/2026"})
            with urllib.request.urlopen(req,timeout=150) as resp,part.open("wb") as f:
                size=0
                for b in iter(lambda:resp.read(1024*1024),b""):
                    size+=len(b)
                    if size>maxsize: raise RuntimeError("arquivo ultrapassa limite de coleta")
                    f.write(b)
            part.replace(path)
            return
        except Exception as e:
            ex=e
            if part.exists():part.unlink()
            time.sleep(trial+1)
    raise RuntimeError("falha de aquisição "+url+": "+str(ex))

def valid_bu(path,url):
    checksum=path.with_name(path.name+".sha512")
    fetch(url+".sha512",checksum,maxsize=1024*1024)
    hs=set(re.findall(r"\b[a-fA-F0-9]{128}\b",checksum.read_text(encoding="utf-8-sig",errors="replace")))
    if len(hs)!=1 or next(iter(hs)).lower()!=sha512(path):
        raise RuntimeError("SHA-512 BU não coincide com referência TSE")

def each_csv(path,subset=None):
    """Lê CSV em streaming sem materializar 500 mil seções."""
    with zipfile.ZipFile(path) as z:
        members=[s for s in z.namelist() if s.lower().endswith(".csv")]
        if not members:raise RuntimeError("ZIP sem CSV: "+str(path))
        if subset:
            filtered=[s for s in members if subset.lower() in s.lower()]
            if not filtered:raise RuntimeError("nenhum CSV do escopo: "+subset+" em "+str(path))
            members=filtered
        for member in members:
            with z.open(member) as source:
                txt=io.TextIOWrapper(source,encoding="latin-1",newline="")
                reader=csv.DictReader(txt,delimiter=";")
                fields=set(reader.fieldnames or [])
                if not fields:raise RuntimeError("CSV sem cabeçalho "+member)
                yield member, fields, reader
                # CONSUMIDOR DEVE ESGOTAR leitor antes de avançar ao próximo membro

def require(fields,required,member):
    missing=set(required)-fields
    if missing:raise RuntimeError(member+": colunas obrigatórias ausentes "+str(sorted(missing)))

def key(row,with_section=True):
    names=PRINCIPAL if with_section else PRINCIPAL[:3]
    values=tuple(norm(row.get(c)) for c in names)
    if not all(values):raise RuntimeError("chave geográfica incompleta")
    return values

def get_int(row,column):
    t=str(row.get(column) or "").strip()
    if not t or not re.fullmatch(r"\d+",t):
        raise RuntimeError("quantitativo inválido "+column+": "+repr(t))
    return int(t)

def acquire_bu(file,uf):
    result={};raw=0;chosen=0
    for member,fields,reader in each_csv(file):
        require(fields,PRINCIPAL+TRIPLET+("NR_TURNO","CD_CARGO_PERGUNTA"),member)
        for row in reader:
            raw+=1
            if norm(row.get("SG_UF"))!=uf or norm(row["NR_TURNO"])!="2" or norm(row["CD_CARGO_PERGUNTA"])!="1":continue
            chosen+=1
            k=key(row)
            v=tuple(get_int(row,f) for f in TRIPLET)
            if k in result and result[k]!=v:raise RuntimeError("BU presidente com contagens diferentes na mesma seção "+str(k))
            result[k]=v
    if not result:raise RuntimeError("BU sem registros de presidente")
    return result,{"linhas_todas":raw,"linhas_presidente":chosen,"secoes":len(result)}

def acquire_detail(file,uf):
    out={1:{},2:{}}
    rows=0
    # arquivo nacional (pode haver um consolidado ou arquivos por UF; filtrar por SG_UF, sem duplicações ambíguas)
    with zipfile.ZipFile(file) as z:
        members=[s for s in z.namelist() if s.lower().endswith(".csv")]
        if any("BRASIL" in s.upper() for s in members):members=[s for s in members if "BRASIL" in s.upper()]
        if not members:raise RuntimeError("detalhe sem CSV")
        for member in members:
            with z.open(member) as raw:
                reader=csv.DictReader(io.TextIOWrapper(raw,encoding="latin-1",newline=""),delimiter=";")
                require(set(reader.fieldnames or []),PRINCIPAL+TRIPLET+("CD_CARGO","NR_TURNO"),member)
                for row in reader:
                    if norm(row.get("SG_UF"))!=uf or norm(row["CD_CARGO"])!="1" or norm(row["NR_TURNO"]) not in ("1","2"):continue
                    turno=int(row["NR_TURNO"])
                    k=key(row)
                    v=tuple(get_int(row,f) for f in TRIPLET)
                    if k in out[turno] and out[turno][k]!=v:
                        raise RuntimeError(f"detalhe com conflito em {k}, turno {turno}")
                    out[turno][k]=v
                    rows+=1
    if not out[1] or not out[2]:raise RuntimeError("detalhe sem as duas rodadas presidenciais para "+uf)
    return out,{"linhas":rows,"secoes_turno1":len(out[1]),"secoes_turno2":len(out[2])}

def acquire_elo(file,uf):
    raw=0;totals=defaultdict(lambda:[0,0,0])
    subset="perfil_comparecimento_abstencao_2026_"+uf+".csv"
    for member,fields,reader in each_csv(file,subset=subset):
        require(fields,PRINCIPAL[:3]+("NR_TURNO","QT_APTOS","QT_COMPARECIMENTO","QT_ABSTENCAO"),member)
        for row in reader:
            if norm(row["SG_UF"])!=uf or norm(row["NR_TURNO"]) not in ("1","2"):continue
            k=(int(row["NR_TURNO"]),)+key(row,False)
            vals=[get_int(row,c) for c in ("QT_APTOS","QT_COMPARECIMENTO","QT_ABSTENCAO")]
            for i in range(3):totals[k][i]+=vals[i]
            raw+=1
    if not totals:raise RuntimeError("ELO sem município/zona: "+uf)
    return {k:tuple(v) for k,v in totals.items()},{"linhas":raw,"zona_turno":len(totals)}

def acquire_perfil(file,uf):
    raw=0;totals=defaultdict(lambda:[0,0,0])
    for member,fields,reader in each_csv(file):
        require(fields,PRINCIPAL+("QT_ELEITORES","QT_ELEITORES_BIOMETRIA","QT_ELEITORES_DEFICIENCIA"),member)
        for row in reader:
            if norm(row["SG_UF"])!=uf:continue
            k=key(row)
            vals=[get_int(row,c) for c in ("QT_ELEITORES","QT_ELEITORES_BIOMETRIA","QT_ELEITORES_DEFICIENCIA")]
            for i in range(3):totals[k][i]+=vals[i]
            raw+=1
    if not totals:raise RuntimeError("perfil sem seção")
    return {k:tuple(v) for k,v in totals.items()},{"linhas":raw,"secoes":len(totals)}

def reconcile(bu,detail,elo,perfil,uf):
    stats=Counter();exceptions=[]
    for section in sorted(set(bu)|set(detail[1])|set(detail[2])|set(perfil)):
        b=bu.get(section);d1=detail[1].get(section);d2=detail[2].get(section);p=perfil.get(section)
        if b and d2:
            stats["BU_e_detalhe_2T_ambos"]+=1
            if b!=d2:
                stats["BU_e_detalhe_2T_divergentes"]+=1
                exceptions.append({"tipo":"BU_VS_DETALHE_2T","uf":uf,"seção":list(section),
                    "bu":b,"detalhe_2t":d2,
                    "status":"DIFERENCA_DOCUMENTAL_A_EXPLICAR"})
        else:
            stats["BU_ou_detalhe_2T_sem_cobertura"]+=1
            exceptions.append({"tipo":"AUSENCIA_DE_FONTE_2T","uf":uf,"seção":list(section),
                               "tem_bu":bool(b),"tem_detalhe":bool(d2),"status":"COBERTURA_INCOMPLETA"})
        if d1 and d2:
            stats["secoes_com_dois_turnos"]+=1
            # registrado, não "suspeita"; população e regras podem variar entre os turnos.
            if d1[0]!=d2[0]:stats["secoes_aptos_distintos_entre_turnos"]+=1
            if d1[1]!=d2[1]:stats["secoes_comparecimento_distinto_entre_turnos"]+=1
        if p and d2:
            stats["perfil_e_detalhe_2T_ambos"]+=1
            if p[0]!=d2[0]:
                stats["perfil_aptos_diferentes_2T"]+=1
                # snapshots em datas diferentes e TTE; diferenças NÃO classificadas como fraude.
            if p[1]>p[0]:
                stats["secoes_biometria_maior_que_eleitorado_perfil"]+=1
        for label,v in (("bu",b),("detalhe_1t",d1),("detalhe_2t",d2)):
            if v and v[0] != v[1]+v[2]:
                stats["desbalanceamento_"+label]+=1
                exceptions.append({"tipo":"APTOS_NE_COMPARECIMENTO_MAIS_ABSTENCAO","uf":uf,
                    "seção":list(section),"origem":label,"valores":v,
                    "status":"VERIFICAR_REGRAS_DE_AGREGACAO_E_TTE"})
    allzones=set(elo)|{(turn,)+k[:3] for turn,detailturn in detail.items() for k in detailturn}
    zonal=defaultdict(lambda:[0,0,0])
    for turno,d in detail.items():
        for k,v in d.items():
            out=zonal[(turno,)+k[:3]]
            for i in range(3):out[i]+=v[i]
    for zon in sorted(allzones):
        e=elo.get(zon);d=zonal.get(zon)
        if e and d:
            stats["zonas_ELO_e_detalhe_ambos"]+=1
            if e!=tuple(d):
                stats["zonas_ELO_e_detalhe_diferentes"]+=1
                exceptions.append({"tipo":"ELO_VS_DETALHE_ZONA","uf":uf,
                    "turno":zon[0],"zona":list(zon[1:]),"elo":e,"detalhe_agregado":d,
                    "status":"DIFERENCA_DE_FONTE_OU_UNIVERSO_REVISAR_TTE"})
        else:
            stats["zonas_sem_cobertura_ambos"]+=1
            exceptions.append({"tipo":"AUSENCIA_DE_FONTE_ZONA","uf":uf,
                "turno":zon[0],"zona":list(zon[1:]),"tem_elo":bool(e),"tem_detalhe":bool(d),
                "status":"COBERTURA_INCOMPLETA"})
    stats["excecoes_documentais"]=len(exceptions)
    return dict(stats),exceptions

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--uf",default="AC")
    ap.add_argument("--data-dir",type=pathlib.Path,default=pathlib.Path("fontes-coerencia"))
    ap.add_argument("--output-dir",type=pathlib.Path,default=pathlib.Path("resultado-coerencia"))
    args=ap.parse_args()
    uf=args.uf.upper()
    if not re.fullmatch(r"[A-Z]{2}",uf):raise ValueError("UF inválida")
    args.data_dir.mkdir(parents=True,exist_ok=True)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    report={"consulta_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"uf":uf,
            "status":"INCOMPLETE","sources":{},"tests":{},
            "errors":[],"limitations":[
              "Sem CPF, nomes, inscrições individuais ou indicação de óbitos.",
              "Todos os arquivos vêm do mesmo órgão; cruzamento verifica consistência documental.",
              "Diferenças entre o ELO e o BU podem decorrer de universo, data de extração, seção agregada ou TTE.",
              "A cobertura nacional depende da execução em cada UF, não se infere do piloto."
            ]}
    try:
        files={}
        for kind,template in URLS.items():
            url=template.format(uf=uf)
            path=args.data_dir/url.rsplit("/",1)[-1]
            fetch(url,path)
            if kind=="bu":valid_bu(path,url)
            files[kind]=path
            report["sources"][kind]={"url":url,"sha512_local":sha512(path),"bytes":path.stat().st_size,
                "verificacao_hash_publicado":"MATCH" if kind=="bu" else "NAO_CONFERIDO"}
        a,report["sources"]["bu"]["metrics"]=acquire_bu(files["bu"],uf)
        b,report["sources"]["detalhe"]["metrics"]=acquire_detail(files["detalhe"],uf)
        c,report["sources"]["elo"]["metrics"]=acquire_elo(files["elo"],uf)
        d,report["sources"]["perfil"]["metrics"]=acquire_perfil(files["perfil"],uf)
        report["tests"],exception=reconcile(a,b,c,d,uf)
        with (args.output_dir/"excecoes_por_secao_zona.jsonl").open("w",encoding="utf-8") as f:
            for row in exception:f.write(json.dumps(row,ensure_ascii=False)+"\n")
        report["status"]="COMPLETE_FOR_PUBLIC_AGGREGATE_RECONCILIATION"
    except Exception as ex:
        report["errors"].append(f"{type(ex).__name__}: {ex}")
    (args.output_dir/"manifesto_coerencia_publica.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    raise SystemExit(0 if report["status"].startswith("COMPLETE") else 2)

if __name__=="__main__":main()
