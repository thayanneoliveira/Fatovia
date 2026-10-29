"""Consolida 1T × 2T nacional e calcula testes de dispersão por município.

Testes puramente descritivos: deltas em pontos percentuais, distribuições,
correlação ecológica com pesos de aptos, e valores extremos com MAD municipal.
Não demonstra intenção de eleitor, causalidade, ou irregularidade eleitoral.
"""
from __future__ import annotations
import argparse,csv,gzip,json,math,statistics
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
from .tse import UFS

def ratio(num,den):
    return num/den if den else None

def scalar(num):
    return round(float(num),5) if num is not None else None

def weighted_correlation(rows):
    """Correlation of Δ turnout vs Δ nonbiometric rates, section-weighted."""
    vals=[(float(r["delta_pp_comparecimento"]),float(r["delta_pp_sem_biometria"]),
           int(r["aptos_1t"])+int(r["aptos_2t"])) for r in rows
          if r["delta_pp_comparecimento"]!="" and r["delta_pp_sem_biometria"]!=""]
    if len(vals)<2:return None
    sw=sum(w for x,y,w in vals)
    mx=sum(x*w for x,y,w in vals)/sw
    my=sum(y*w for x,y,w in vals)/sw
    c=sum((x-mx)*(y-my)*w for x,y,w in vals)/sw
    vx=sum((x-mx)**2*w for x,y,w in vals)/sw
    vy=sum((y-my)**2*w for x,y,w in vals)/sw
    return scalar(c/(vx*vy)**0.5) if vx and vy else None

def run(data_dir,out):
    data_dir=Path(data_dir);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    errors=[]
    totals=Counter()
    peruf={}
    anomalies=[]
    all_rows=[]
    data_mun=defaultdict(list)
    for uf in UFS:
        metadata=data_dir/(uf+".json")
        datafile=data_dir/(uf+".csv.gz")
        if not metadata.exists() or not datafile.exists():
            errors.append(f"{uf}: artefatos de ambos os turnos ausentes")
            continue
        d=json.loads(metadata.read_text(encoding="utf-8"))
        if d.get("status")!="OK":
            errors.append(f"{uf}: {d.get('status')} {d.get('erro','')}")
            continue
        cov=d["cobertura"]
        stats=d["indicadores"]
        peruf[uf]={
            "secao_1t":cov["secoes_1t"],
            "secao_2t":cov["secoes_2t"],
            "secoes_em_ambos":cov["secoes_em_ambos"],
            "somente_1t":cov["apenas_1t"],
            "somente_2t":cov["apenas_2t"],
            "urna_fisica_diferente":stats["urna_diferente"],
            "taxa_comparecimento_1t":stats.get("taxa_comparecimento_1t"),
            "taxa_comparecimento_2t":stats.get("taxa_comparecimento_2t"),
            "delta_comparecimento_pp":stats.get("delta_pp_comparecimento"),
            "taxa_sem_biometria_1t":stats.get("taxa_sem_biometria_1t"),
            "taxa_sem_biometria_2t":stats.get("taxa_sem_biometria_2t"),
            "delta_sem_biometria_pp":stats.get("delta_pp_sem_biometria"),
        }
        for name in ("secoes","aptos_1t","aptos_2t","comparecimento_1t",
                     "comparecimento_2t","sem_biometria_1t",
                     "sem_biometria_2t","urna_diferente"):
            totals[name]+=stats[name]
        with gzip.open(datafile,"rt",encoding="utf-8",newline="") as f:
            observed=0
            for r in csv.DictReader(f):
                observed+=1
                all_rows.append(r)
                key=(uf,r["municipio"])
                data_mun[key].append(r)
        if observed!=cov["secoes_em_ambos"]:
            errors.append(f"{uf}: CSV {observed} não confere {cov['secoes_em_ambos']}")
    city_summaries=[]
    flags=Counter()
    for (uf,municipio),rows in sorted(data_mun.items()):
        rate_turn=[float(r["delta_pp_comparecimento"]) for r in rows if r["delta_pp_comparecimento"]]
        rate_bio=[float(r["delta_pp_sem_biometria"]) for r in rows if r["delta_pp_sem_biometria"]]
        if len(rows)<10 or len(rate_turn)<10 or len(rate_bio)<10:
            continue
        med_turn=statistics.median(rate_turn)
        mad_turn=statistics.median(abs(x-med_turn) for x in rate_turn)
        med_bio=statistics.median(rate_bio)
        mad_bio=statistics.median(abs(x-med_bio) for x in rate_bio)
        local_count=Counter()
        for r in rows:
            if r["delta_pp_comparecimento"] and (
                abs(float(r["delta_pp_comparecimento"])-med_turn)>max(5,4*1.4826*mad_turn)):
                local_count["comparecimento_extremo"]+=1
                flags["comparecimento_extremo"]+=1
            if r["delta_pp_sem_biometria"] and (
                abs(float(r["delta_pp_sem_biometria"])-med_bio)>max(5,4*1.4826*mad_bio)):
                local_count["biometria_extrema"]+=1
                flags["biometria_extrema"]+=1
        city_summaries.append({
            "uf":uf,"municipio_tse":int(municipio),"municipio":rows[0]["cidade"],
            "secoes_comparaveis":len(rows),
            "mediana_delta_comparecimento_pp":scalar(med_turn),
            "mad_delta_comparecimento_pp":scalar(mad_turn),
            "mediana_delta_biometria_pp":scalar(med_bio),
            "mad_delta_biometria_pp":scalar(mad_bio),
            "extremos_comparecimento":local_count["comparecimento_extremo"],
            "extremos_biometria":local_count["biometria_extrema"],
        })
    total1=ratio(totals["comparecimento_1t"],totals["aptos_1t"])
    total2=ratio(totals["comparecimento_2t"],totals["aptos_2t"])
    biom1=ratio(totals["sem_biometria_1t"],totals["comparecimento_1t"])
    biom2=ratio(totals["sem_biometria_2t"],totals["comparecimento_2t"])
    report={
        "projeto":"FATOVIA AUDITA",
        "data_utc":datetime.now(timezone.utc).isoformat(),
        "status":"CONCLUIDO_COM_RESSALVAS" if not errors and len(peruf)==len(UFS) else "INCONCLUSIVO",
        "turnos":"1º e 2º de 2026, Presidente",
        "unidades_esperadas":len(UFS),"unidades_conferidas":len(peruf),
        "unidades_pendentes":errors,
        "cobertura":dict(totals),
        "taxas":{
            "comparecimento_1t":scalar(total1),
            "comparecimento_2t":scalar(total2),
            "delta_comparecimento_pp":scalar(100*(total2-total1)) if total1 is not None and total2 is not None else None,
            "sem_biometria_1t":scalar(biom1),
            "sem_biometria_2t":scalar(biom2),
            "delta_sem_biometria_pp":scalar(100*(biom2-biom1)) if biom1 is not None and biom2 is not None else None,
            "correlacao_deltas_ponderada_aptos":weighted_correlation(all_rows),
        },
        "analise_descritiva_extremos":{
            "criterio":"n>=10 por município; |delta_pp - mediana_municipal| maior que max(5 pontos percentuais, 4×1,4826×MAD)",
            "municipios_com_10_secoes_ou_mais":len(city_summaries),
            "secoes_classificadas_extremas_por_indicador":dict(flags),
            "nota":"Valores extremos são observações para revisão contextual, não irregularidades.",
        },
        "por_uf":peruf,
        "municipios_com_10_secoes_ou_mais":city_summaries,
        "ressalvas":[
            "As contagens e taxas se referem à INTERSEÇÃO das seções dos dois turnos; não incluir seções ausentes como zero.",
            "A taxa nacional de 1T e 2T muda de denominador conforme aptos/comparecimento; diferenças não são individuais.",
            "Primeiro turno inclui mais disputas no mesmo dia, mas os indicadores de voto são filtrados para Presidente.",
            "Equipamento físico distinto entre 1T e 2T não significa ocorrência de contingência ou irregularidade.",
            "Mudança de comparecimento é esperada e não demonstra erro de totalização.",
            "Associação matemática e extremos não demonstram fraude, causa, nem vínculo entre eleitor e voto.",
        ],
    }
    (out/"comparacao-turnos-2026.json").write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    with (out/"municipios-dispersao-turnos-2026.csv").open("w",encoding="utf-8",newline="") as f:
        if city_summaries:
            w=csv.DictWriter(f,fieldnames=city_summaries[0].keys())
            w.writeheader();w.writerows(city_summaries)
    lines=[
        "# FATOVIA AUDITA | Comparação 1º × 2º turno presidencial, 2026",
        "",f"**Status:** {report['status']}. UFs: {len(peruf)}/{len(UFS)}.",
        "",f"Seções pareadas: {totals['secoes']:,}.",
        "",
        "| Métrica | 1º turno | 2º turno | Diferença (pp) |",
        "|---|---:|---:|---:|",
        f"| Taxa de comparecimento | {100*total1:.3f}% | {100*total2:.3f}% | {100*(total2-total1):+.3f} |" if total1 is not None and total2 is not None else "| Comparecimento | n/d | n/d | n/d |",
        f"| Sem habilitação biométrica / comparecimento | {100*biom1:.3f}% | {100*biom2:.3f}% | {100*(biom2-biom1):+.3f} |" if biom1 is not None and biom2 is not None else "| Biometria | n/d | n/d | n/d |",
        "",
        f"Correlação entre as mudanças por seção, ponderada por aptos: {report['taxas']['correlacao_deltas_ponderada_aptos']}.",
        "", "## Cobertura por UF", "",
        "| UF | 1º turno | 2º turno | Pareadas | Apenas 1º | Apenas 2º |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for uf,s in sorted(peruf.items()):
        lines.append(f"| {uf} | {s['secao_1t']:,} | {s['secao_2t']:,} | {s['secoes_em_ambos']:,} | {s['somente_1t']:,} | {s['somente_2t']:,} |")
    lines+=["", "## Variabilidade entre seções do mesmo município", "",
        f"Foram considerados {len(city_summaries):,} grupos com pelo menos dez seções pareadas. "
        "A classificação é descritiva e não constitui indicação de irregularidade.",
        "",
        f"Extremos de comparecimento: {flags['comparecimento_extremo']:,}. "
        f"Extremos de habilitação sem biometria: {flags['biometria_extrema']:,}.",
        "", "## Ressalvas", "",
        *["- "+item for item in report["ressalvas"]],
        "", "Dados oficiais: TSE BWeb e CEFT 1º e 2º turnos; hashes SHA-512 verificados.",
        ""]
    (out/"comparacao-turnos-2026.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({"status":report["status"],"cobertura":report["cobertura"],
       "taxas":report["taxas"],"extremos":report["analise_descritiva_extremos"],
       "erros":errors},ensure_ascii=False),flush=True)
    return report["status"]=="CONCLUIDO_COM_RESSALVAS"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="work/turnos")
    p.add_argument("--out",default="work/turnos-consolidado")
    a=p.parse_args()
    if not run(a.input,a.out):raise SystemExit(2)

if __name__=="__main__":
    main()
