"""Consolidação de cruzamento BWeb × CEFT × horário de encerramento.

A conclusão se refere a sobreposição de grupos, não a horário de troca:
CEFT não traz timestamp de contingência. Confrontar critérios do relatório
TSE divulgado em 27/10 antes de inferir horas por localidade.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import json,csv,argparse

UF_TSE_1710={
"AC":33,"AL":241,"AM":347,"AP":47,"BA":3787,"CE":408,
"DF":696,"ES":105,"GO":205,"MA":865,"MG":740,"MS":97,
"MT":268,"PA":701,"PB":579,"PE":1872,"PI":237,"PR":243,
"RJ":5713,"RN":238,"RO":102,"RR":43,"RS":220,"SC":98,
"SE":187,"SP":6093,"TO":103}

def run(indir,outdir):
    indir,outdir=Path(indir),Path(outdir)
    outdir.mkdir(parents=True,exist_ok=True)
    byuf={}
    absent=[]
    totals=Counter()
    rows=[]
    for uf in (*UF_TSE_1710,"ZZ"):
        path=indir/(uf+".json")
        if not path.exists():
            absent.append(uf)
            continue
        d=json.loads(path.read_text(encoding="utf-8"))
        if d["status"]!="EXECUTADO_REQUER_VALIDACAO_FUSO":
            absent.append(uf)
            continue
        c=d["temporal"]["contagens"]
        byuf[uf]=dict(c)
        for k,v in c.items():
            totals[k]+=v
        if uf=="ZZ":
            byuf[uf]["comparacao_tse_1710"]="NAO_APLICAVEL_EXTERIOR"
        else:
            ext=c["depois_17h10"]
            expected=UF_TSE_1710[uf]
            byuf[uf]["tse_secoes_encerradas_depois_17h10"]=expected
            byuf[uf]["diferenca_bweb_menos_tse"]=ext-expected
            byuf[uf]["horario_do_bweb_conferido_com_tse"]=ext==expected
        for r in d["temporal"].get("amostra_secoes_coincidentes",[]):
            rows.append(r)
    ratios={}
    for label,swap,anycount in [
        ("apos_17h10","trocadas_encerradas_depois_17h10","depois_17h10"),
        ("apos_19h","trocadas_encerradas_depois_19h","depois_19h"),
    ]:
        n=totals["total"]
        s=totals["trocadas"]
        a=totals[anycount]
        intersection=totals[swap]
        ratios[label]={
            "secoes_trocadas_total":s,
            "secoes_apos_corte":a,
            "secoes_trocadas_e_apos_corte":intersection,
            "proporcao_apos_corte_entre_trocadas":intersection/s if s else None,
            "proporcao_apos_corte_entre_nao_trocadas":(
                (a-intersection)/(n-s) if n>s else None),
            "comparacao_somente_descritiva":True,
        }
    if len(byuf)!=28:
        status="INCONCLUSIVO_PENDENCIAS"
    elif any(not item.get("horario_do_bweb_conferido_com_tse",True) for item in byuf.values()):
        status="CRUZAMENTO_EXECUTADO_VALIDACAO_TSE_PENDENTE"
    else:
        status="CRUZAMENTO_TEMPORAL_VALIDADO"
    report={
        "projeto":"FATOVIA AUDITA","gerado_utc":datetime.now(timezone.utc).isoformat(),
        "status":status,"ufs_processadas":len(byuf),"ufs_pendentes":absent,
        "escopo":"Associação entre diferença de urna prevista/efetivada e horário de encerramento de seção em 25/10/2026",
        "fontes":["BWeb e CEFT oficiais TSE 2º turno com SHA512 conferido",
            "TSE 27/10/2026: boletim nacional seções após 17h10 (comparação de critério)"],
        "totais":dict(totals),"proporcoes":ratios,"por_uf":byuf,
        "horarios_tse_nao_reproduzidos_em":{
            uf:x["diferenca_bweb_menos_tse"] for uf,x in byuf.items()
            if uf!="ZZ" and not x["horario_do_bweb_conferido_com_tse"]},
        "limites":[
            "CEFT informa substituição/desvio de equipamento entre o esperado e o efetivado, não a hora da troca.",
            "Encerramento depois das 17h não prova utilização da extensão extraordinária.",
            "O corte do TSE de 17h10 pode utilizar outro critério, fuso ou registro; divergências devem ser explicadas antes de inferências.",
            "Trocas de urna durante a votação são procedimentos possíveis pela regulamentação em vigor, com registro obrigatório.",
            "Correlação numérica entre troca e horário tardio não comprova causalidade, regularidade ou fraude.",
        ]}
    (outdir/"trocas-horarios-2026.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    with (outdir/"amostra-secoes-trocadas-horario-tardio.csv").open("w",newline="",encoding="utf-8") as f:
        if rows:
            w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    md=[
        "# FATOVIA AUDITA | Urnas prevista/efetivada e encerramento de seções, 2026",
        "",f"**Status:** {status}. UFs verificadas {len(byuf)}/28.",
        "",
        "**Limite central:** não há nos dados CEFT o horário da troca. Um encerramento depois de 17h10 não comprova troca tardia.",
        "",
        "| UF | Seções | Urnas distintas da previsão | Encerradas após 17h10 (BU) | Dessas, com urna diferente | TSE após 17h10 | Compatível? |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for uf,x in sorted(byuf.items()):
        md.append(f"| {uf} | {x['total']:,} | {x['trocadas']:,} | "
             f"{x['depois_17h10']:,} | {x['trocadas_encerradas_depois_17h10']:,} | "
             f"{x.get('tse_secoes_encerradas_depois_17h10','n/a')} | "
             f"{'sim' if x.get('horario_do_bweb_conferido_com_tse',True) else 'não'} |")
    md+=["","## Total nacional (incluindo exterior, se disponível)","",
         f"- Seções com números diferentes de urna prevista e efetivada: {totals['trocadas']:,}.",
         f"- Seções com essa diferença e encerramento após 17h10: {totals['trocadas_encerradas_depois_17h10']:,}.",
         f"- Seções com essa diferença e encerramento após 19h: {totals['trocadas_encerradas_depois_19h']:,}.",
         "","## Ressalvas e solicitações objetivas",""]
    md.extend("- "+x for x in report["limites"])
    md+=["","Para estabelecer se ocorreu troca DEPOIS das 17h, solicitar a ata, horário do Ocorre JE, identificação das urnas anterior/efetiva e logs originais assinados.",
         ""]
    (outdir/"trocas-horarios-2026.md").write_text("\n".join(md),encoding="utf-8")
    print(json.dumps({"status":status,"uf":len(byuf),"totais":dict(totals),
      "incompatibilidades_tse":len(report["horarios_tse_nao_reproduzidos_em"]),
      "ausentes":absent},ensure_ascii=False),flush=True)
    return bool(byuf)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="work/horarios")
    p.add_argument("--out",default="work/horarios-consolidados")
    a=p.parse_args()
    if not run(a.input,a.out):raise SystemExit(2)

if __name__=="__main__":main()
