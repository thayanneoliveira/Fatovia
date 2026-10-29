"""Consolida critérios temporais de DT_ENCERRAMENTO do BWeb nas 27 UFs."""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import argparse,json
from .consolidar_trocas_horarios_2026 import UF_TSE_1710

def consolidate(indir,outdir):
    indir=Path(indir);outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    keys=["depois_17:00","depois_17:02","depois_17:05","depois_17:10",
          "depois_17:15","depois_18:00","depois_19:00"]
    sums=Counter()
    state={}
    errors=[]
    for uf in UF_TSE_1710:
        f=indir/(uf+".json")
        if not f.exists():
            errors.append(f"{uf}: sem artefato");continue
        d=json.loads(f.read_text(encoding="utf-8"))
        if d["status"]=="INCONCLUSIVO":
            errors.append(f"{uf}: {d.get('erro')}");continue
        row=d["dados"]
        state[uf]={"secoes_bweb":row["secoes_bweb"],
            "tse_pos_17h10":row["tse_secoes_apos_17h10"],
            "bweb_pos_17h10":row["contagem_criterios"].get("depois_17:10",0),
            "diferenca_bweb_menos_tse":row["diferenca_bweb_menos_tse"],
            "contagem_cortes":{k:row["contagem_criterios"].get(k,0) for k in keys}}
        sums["secoes_bweb"]+=row["secoes_bweb"]
        sums["tse_pos_17h10"]+=row["tse_secoes_apos_17h10"]
        for k in keys:
            sums[k]+=row["contagem_criterios"].get(k,0)
    out={
        "status":"27_UFS_ANALISADAS_CRITERIOS_DIVERGEM" if not errors and sums["depois_17:10"]!=sums["tse_pos_17h10"] else
                 "INCONCLUSIVO" if errors else "27_UFS_VALORES_COINCIDEM_NAO_CONFERIDA_EQUIVALENCIA",
        "data_utc":datetime.now(timezone.utc).isoformat(),
        "ufs_conferidas":len(state),"ufs_previstas":27,
        "totais":dict(sums),"por_uf":state,"erros":errors,
        "ressalvas":[
            "O critério declarado pelo TSE para permanecer aberta após 17h10 pode não corresponder ao campo DT_ENCERRAMENTO.",
            "Os cortes alternativos são exploratórios e não constituem equivalência comprovada.",
            "Diferença entre totais exige documentação dos critérios, não constitui por si só irregularidade.",
            "Horário de encerramento não é horário de substituição nem horário de cada voto.",
        ]
    }
    (outdir/"horarios-metodologia-2026.json").write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    lines=["# FATOVIA AUDITA | Reconciliação de cortes BWeb/TSE",
           "",f"**Status:** {out['status']}. **UFs:** {len(state)}/27.", "",
           "O TSE divulgou 24.268 seções que permaneceram abertas após 17h10. O teste abaixo",
           "conta por critério explícito o campo DT_ENCERRAMENTO do BWeb. Essa variável",
           "pode representar um evento operacional diferente e os totais não devem ser",
           "interpretados como mesmo fenômeno sem confirmação da metodologia.",
           "","| Critério | Seções (soma das 27 UFs) |","|---|---:|"]
    for k in keys:
        lines.append(f"| BWeb {k} | {sums.get(k,0):,} |")
    lines.append(f"| Levantamento TSE após 17h10 | {sums['tse_pos_17h10']:,} |")
    lines += ["","## Por UF","","| UF | TSE após 17h10 | BWeb após 17h10 | Diferença |",
              "|---|---:|---:|---:|"]
    for uf,r in sorted(state.items()):
        lines.append(f"| {uf} | {r['tse_pos_17h10']:,} | {r['bweb_pos_17h10']:,} | {r['diferenca_bweb_menos_tse']:+,} |")
    lines += ["","## Perguntas a esclarecer junto ao TSE","",
        "- Qual é a definição operacional de 'permanecer aberta após 17h10' no levantamento de 27/10?",
        "- Foi utilizado DT_ENCERRAMENTO, hora do último evento de voto, impressão do BU ou outra marca?",
        "- Que seções foram excluídas e por quais códigos de situação, origem do voto ou fuso?",
        "- Os dados do BWeb e do levantamento foram extraídos da mesma versão e no mesmo instante?",
        "- Há dicionário de campos com critérios de ajuste de horário de Brasília e contingências?",
        "", "## Limitações", "",
        *["- "+s for s in out["ressalvas"]],
        "", "Fonte TSE: https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/eleicoes-2026-mais-de-34-mil-votos-foram-registrados-apos-as-17h-no-2o-turno", ""]
    (outdir/"horarios-metodologia-2026.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({"status":out["status"],"ufs":len(state),"totais":dict(sums),"erros":errors},ensure_ascii=False),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    consolidate(a.input,a.out)
