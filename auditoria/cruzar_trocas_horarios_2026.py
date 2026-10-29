"""Auditoria de correspondências de urna × horário de encerramento do BU, 2026/2T.

Compara a URNA PREVISTA vs EFETIVADA (CEFT) com horário de encerramento
da seção (BWeb). Não atribui data/hora à SUBSTITUIÇÃO: CEFT não contém
hora da troca. Encerramento tardio != urna trocada tardiamente.

Conferência de todos os arquivos por SHA512 oficial e baseline 28/10.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import csv,gzip,json,re

from .tse import UFS,csv_rows
from .ma_integral import checked_reference

BASELINE=Path("docs/auditoria/2026-2t-presidente.json")
OUTPUT_FIELDS=("uf","cod_municipio_tse","municipio","zona","secao",
    "urna_prevista","urna_efetivada","tipo_divergencia",
    "encerramento_original","hora_extraida","encerramento_apos_17h10",
    "encerramento_apos_19h","observacao")
CUTOFF17=17*3600+10*60
CUTOFF19=19*3600

def parse_time(value):
    s=(value or "").strip()
    if not s:return None
    # Suporta DD/MM/AAAA HH:MM:SS, AAAA-MM-DD HH:MM:SS, HH:MM:SS.
    m=re.search(r"(?<!\d)([012]?\d):([0-5]\d)(?::([0-5]\d))?(?!\d)",s)
    if not m:return None
    h,minute,sec=(int(m.group(1)),int(m.group(2)),int(m.group(3) or 0))
    if h>23:return None
    return h*3600+minute*60+sec

def bucket(seconds):
    if seconds is None:return "SEM_HORA"
    if seconds>19*3600:return "DEPOIS_19_00"
    if seconds>17*3600+10*60:return "DEPOIS_17_10_ATE_19_00"
    return "ATE_17_10"

def read_bweb_times(path,uf):
    info={}
    samples=[]
    columns=[]
    time_columns=[]
    for row in csv_rows(path):
        if not columns:
            columns=list(row.keys())
            time_columns=[x for x in columns if any(v in x.upper() for v in ("ENCERR","HORARIO","HORA","RECEBIDO","FUSO"))]
        if row.get("NR_TURNO")!="2" or row.get("CD_CARGO_PERGUNTA")!="1":
            continue
        if row["SG_UF"]!=uf:raise ValueError("UF BWeb não corresponde à esperada")
        key=tuple(int(row[k]) for k in ("CD_MUNICIPIO","NR_ZONA","NR_SECAO"))
        time_value=row.get("DT_ENCERRAMENTO","")
        hour_value=row.get("HH_ENCERRAMENTO","")
        value=(time_value+" "+hour_value).strip()
        time=parse_time(hour_value) if hour_value else parse_time(time_value)
        if key not in info:
            info[key]={"raw":value,"second":time,
                       "cidade":row.get("NM_MUNICIPIO",""),
                       "sample":{k:row.get(k) for k in time_columns}}
            if len(samples)<12:
                samples.append({"secao":list(key),**info[key]["sample"]})
        else:
            if info[key]["raw"]!=value:
                raise ValueError(f"Horário divergente entre linhas BU da mesma seção {key}")
    return info,{"columns":time_columns,"samples":samples}

def read_geography(path,uf):
    rows={}
    with gzip.open(path,"rt",encoding="utf-8",newline="") as fp:
        for r in csv.DictReader(fp):
            if r["uf"]!=uf:raise ValueError("UF base geográfica incorreta")
            key=(int(r["cod_municipio_tse"]),int(r["zona"]),int(r["secao"]))
            if key in rows:raise ValueError("Seção duplicada base geográfica")
            rows[key]=r
    return rows

def inspect_uf(uf,geodir,outdir):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    result={
        "uf":uf,"gerado_utc":datetime.now(timezone.utc).isoformat(),
        "status":"INCONCLUSIVO","fontes":{},"cobertura":{},"temporal":{},
        "ressalvas":[
            "Encerramento posterior a 17h ou 19h NÃO significa voto após o horário.",
            "Divergência entre número de urna prevista e efetivada NÃO possui timestamp da troca no CEFT.",
            "A escala de horários precisa ser confrontada com tabelas do TSE, inclusive ajuste para horário de Brasília.",
            "Substituição de urna defeituosa durante votação é permitida pela Resolução TSE 23.751/2026, art. 147.",
            "Sem ata Ocorre JE e registros de contingência, horário exato da troca é desconhecido.",
        ],
        "secoes_coincidentes":[],"secoes_trocadas":[]}
    try:
        snap=json.loads(BASELINE.read_text(encoding="utf-8"))["arquivos_por_uf"][uf]
        geo=read_geography(Path(geodir)/(uf+".csv.gz"),uf)
        with TemporaryDirectory(prefix=f"fatovia-temporal-{uf}-") as temp:
            bufile,metadata=checked_reference(snap["url"],"bu.zip",temp)
            if metadata["sha512"]!=snap["sha512_calculado"]:
                raise ValueError("BU difere da referência 28/10")
            times,inspection=read_bweb_times(bufile,uf)
        if set(geo)!=set(times):
            raise ValueError(f"Chaves não coincidentes BWeb × CEFT: {(len(set(geo)-set(times)),len(set(times)-set(geo)))}")
        counts=Counter()
        table=Counter()
        unparsed=[]
        examples=[]
        with (outdir/(uf+".csv")).open("w",encoding="utf-8",newline="") as csvout:
            w=csv.DictWriter(csvout,fieldnames=OUTPUT_FIELDS)
            w.writeheader()
            for key,r in sorted(geo.items()):
                record=times[key]
                t=record["second"]
                swapped=bool(r["urna_prevista"] and r["urna_efetivada"]
                             and r["urna_prevista"]!=r["urna_efetivada"])
                if t is None and len(unparsed)<15:
                    unparsed.append({"key":list(key),"raw":record["raw"]})
                b=bucket(t)
                table[("TROCADA" if swapped else "NAO_TROCADA",b)]+=1
                counts["total"]+=1
                counts["trocadas"]+=swapped
                counts["hora_extraida"]+=t is not None
                if t is not None:
                    counts["depois_17h10"]+=t>CUTOFF17
                    counts["depois_19h"]+=t>CUTOFF19
                if swapped and t is not None and t>CUTOFF17:
                    counts["trocadas_encerradas_depois_17h10"]+=1
                if swapped and t is not None and t>CUTOFF19:
                    counts["trocadas_encerradas_depois_19h"]+=1
                if swapped:
                    record_out={
                        "uf":uf,"cod_municipio_tse":key[0],"municipio":r["nome_municipio"],
                        "zona":key[1],"secao":key[2],
                        "urna_prevista":r["urna_prevista"],"urna_efetivada":r["urna_efetivada"],
                        "tipo_divergencia":r["tipo_divergencia"],
                        "encerramento_original":record["raw"],
                        "hora_extraida":f"{t//3600:02d}:{(t%3600)//60:02d}:{t%60:02d}" if t is not None else "",
                        "encerramento_apos_17h10":int(t>CUTOFF17) if t is not None else "",
                        "encerramento_apos_19h":int(t>CUTOFF19) if t is not None else "",
                        "observacao":"Hora da SUBSTITUIÇÃO não consta no CEFT."
                    }
                    w.writerow(record_out)
                    if t is not None and t>CUTOFF17 and len(examples)<25:
                        examples.append(record_out)
        result["fontes"]={"bweb_2026_2t_sha512":metadata["sha512"],
                          "base_geo":f"GitHub Actions 40877055121/{uf}.csv.gz"}
        result["cobertura"]={"secoes":len(geo),"horarios_validos":counts["hora_extraida"],
                            "amostra_horarios_nao_interpretados":unparsed,
                            "campos_temporais_encontrados":inspection["columns"],
                            "amostra_campos_temporais":inspection["samples"]}
        result["temporal"]={"contagens":dict(counts),
                            "tabela_urna_prevista_efetivada_x_encerramento":{
                                f"{a}|{b}":n for (a,b),n in sorted(table.items())},
                            "amostra_secoes_coincidentes":examples}
        if counts["hora_extraida"]==0:
            result["status"]="INCONCLUSIVO"
            result["erro"]="BWeb não contém horário de encerramento parseável."
        elif counts["hora_extraida"]!=len(geo):
            result["status"]="INCONCLUSIVO"
            result["erro"]="Parte das seções sem timestamp de encerramento interpretável."
        else:
            result["status"]="EXECUTADO_REQUER_VALIDACAO_FUSO"
    except Exception as exc:
        result["erro"]=f"{type(exc).__name__}: {exc}"
        result["status"]="INCONCLUSIVO"
    (outdir/(uf+".json")).write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"uf":uf,"status":result["status"],"cobertura":result["cobertura"],
                      "temporal":result["temporal"].get("contagens"),
                      "tabela":result["temporal"].get("tabela_urna_prevista_efetivada_x_encerramento"),
                      "erro":result.get("erro")},ensure_ascii=False),flush=True)
    return result["status"]=="EXECUTADO_REQUER_VALIDACAO_FUSO"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--uf",choices=UFS,required=True)
    p.add_argument("--geodir",default="work/base2t")
    p.add_argument("--out",default="work/horarios-trocas")
    a=p.parse_args()
    if not inspect_uf(a.uf,a.geodir,a.out):raise SystemExit(2)

if __name__=="__main__":
    main()
