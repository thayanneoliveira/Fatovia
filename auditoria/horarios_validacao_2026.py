"""Valida critério de encerramento por UF sem igualar indevidamente BWeb e TSE.

Contagem de DT_ENCERRAMENTO do BWeb por cortes documentados (17h, 17h02,
17h05, 17h10, 17h15, 19h) e comparação com o agregado divulgado pelo TSE.
Se não coincidir, classifica como DIFERENCA_DE_CRITERIO, não fraude.
"""
from __future__ import annotations
import argparse,json
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from .cruzar_trocas_horarios_2026 import read_bweb_times
from .ma_integral import checked_reference
from .consolidar_trocas_horarios_2026 import UF_TSE_1710

CUTS=(17*60,17*60+2,17*60+5,17*60+10,17*60+15,18*60,19*60)

def run(uf,outdir):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    report={"uf":uf,"gerado_utc":datetime.now(timezone.utc).isoformat(),
            "status":"INCONCLUSIVO","fontes":{},"dados":{},
            "observacoes":[
                "DT_ENCERRAMENTO do BWeb pode não representar o mesmo marco temporal da pesquisa oficial.",
                "TSE informa 24.268 seções permanecendo abertas depois de 17h10, considerando critério próprio.",
                "Nenhum corte alternativo será escolhido para forçar coincidência estatística.",
                "Ausência de explicação sobre diferença temporal não comprova fraude.",
            ]}
    try:
        original=json.loads(Path("docs/auditoria/2026-2t-presidente.json").read_text(encoding="utf-8"))["arquivos_por_uf"][uf]
        with TemporaryDirectory(prefix="fatovia-horario-valid-") as d:
            bufile,meta=checked_reference(original["url"],"bweb.zip",d)
            if meta["sha512"]!=original["sha512_calculado"]:
                raise ValueError("Hash original BU não coincide")
            records,cols=read_bweb_times(bufile,uf)
        counts=Counter()
        byhour=Counter()
        for obj in records.values():
            seconds=obj["second"]
            if seconds is None:
                counts["sem_horario"]+=1;continue
            byhour[f"{seconds//3600:02d}"]+=1
            for cut in CUTS:
                if seconds>cut*60:
                    counts[f"depois_{cut//60:02d}:{cut%60:02d}"]+=1
            if seconds<17*3600:
                counts["antes_17:00"]+=1
            elif seconds==17*3600:
                counts["igual_17:00"]+=1
        value=counts["depois_17:10"]
        tse=UF_TSE_1710[uf]
        report["dados"]={
            "secoes_bweb":len(records),"horarios_ausentes":counts["sem_horario"],
            "contagem_criterios":dict(counts),
            "secoes_por_hora":dict(byhour),
            "tse_secoes_apos_17h10":tse,
            "diferenca_bweb_menos_tse":value-tse,
            "relacao_bweb_sobre_tse":round(value/tse,5) if tse else None,
            "campos_temporais_encontrados":cols["columns"],
        }
        report["fontes"]={"bweb":meta,"estatistica_tse":"https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/eleicoes-2026-mais-de-34-mil-votos-foram-registrados-apos-as-17h-no-2o-turno"}
        report["status"]="CRITERIO_BWEB_DIFERE_TSE" if value!=tse else "CONTAGENS_COINCIDEM_SEM_PROVA_EQUIVALENCIA_METODOLOGICA"
    except Exception as exc:
        report["erro"]=f"{type(exc).__name__}: {exc}"
    (outdir/(uf+".json")).write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"uf":uf,"status":report["status"],"dados":report["dados"],"erro":report.get("erro")},ensure_ascii=False),flush=True)
    return report["status"]!="INCONCLUSIVO"

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--uf",required=True,choices=tuple(UF_TSE_1710))
    p.add_argument("--out",default="work/horarios-validacao")
    a=p.parse_args()
    if not run(a.uf,a.out):raise SystemExit(2)
