"""Reconstroi se urnas efetivadas já tinham eventos de votação antes das 17h.

Escopo: somente CEFT diferente da previsão E BU encerrado após 17h10.
Arquivo público bruto TSE via Range. Evidência de evento no dispositivo
ANTES de 17h permite atestar que a urna estava em atividade nesse momento,
mas não exclui substituições posteriores adicionais e não substitui atas.

Não armazena votos individuais, timestamps de cada evento ou ordem de votos.
"""
from __future__ import annotations
import argparse,csv,json,zipfile
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

import asn1tools
from .brasil_2026 import published_urls,file_index_uf
from . import ma_arqurna_range as range_mod
from .ma_amostra_profunda import SPEC,signature_hashes,compare_hashes
from .investigar_logs_2026 import log_entries

range_mod.MAX_BYTES_TRANSFERRED=800*1024*1024

def read_targets(path):
    items=[]
    import csv
    with Path(path).open("r",encoding="utf-8",newline="") as f:
        for r in csv.DictReader(f):
            if r["encerramento_apos_17h10"]!="1":
                continue
            if not r["urna_efetivada"].isdigit():
                continue
            items.append(r)
    return items

def inspect_log(data,effective):
    texts=log_entries(data)
    union=Counter()
    for t in texts:
        cc=Counter(t.splitlines())
        for line,n in cc.items():
            union[line]=max(union[line],n)
    count=Counter()
    for line,n in union.items():
        fields=line.split("\t")
        if len(fields)<5:continue
        when,_,serial,app,msg=fields[:5]
        if when[:10]!="25/10/2026":
            continue
        if app!="VOTA" or "O voto do eleitor foi computado" not in msg:
            continue
        if not serial.isascii() or not serial.isdigit():continue
        hour=when[11:13]
        minute=when[14:16]
        if not(hour.isdigit() and minute.isdigit()):continue
        s=int(hour)*60+int(minute)
        if int(serial)==int(effective):
            count["efetiva_eventos_antes_17h"]+=n if s<17*60 else 0
            count["efetiva_eventos_apos_17h"]+=n if s>=17*60 else 0
        else:
            count["outra_urna_eventos_antes_17h"]+=n if s<17*60 else 0
            count["outra_urna_eventos_apos_17h"]+=n if s>=17*60 else 0
    return dict(count),len(texts)

def run(uf,targets_path,outdir):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    selected=read_targets(targets_path)
    report={"uf":uf,"data_utc":datetime.now(timezone.utc).isoformat(),
      "selecionadas":len(selected),"examinadas":0,"status":"INCONCLUSIVO",
      "sintese":{},"secoes":{},"erros":[],"limitacoes":[
       "Eventos de voto extraídos dos logs não identificam eleitor, candidato nem horário da troca.",
       "Atividade da urna efetivada antes de 17h indica operação anterior ao corte, mas não exclui outra substituição subsequente.",
       "Ausência de atividade publicada antes de 17h não comprova substituição tardia.",
       "Encerramento após 17h10 não demonstra diretamente influência da prorrogação.",
       "Hash de conteúdo declarado no VSC foi comparado; cadeia de confiança da assinatura não foi validada."
      ]}
    out=outdir/(uf+".json")
    if not selected:
        report["status"]="SEM_SECOES_COMBINADAS"
        out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"uf":uf,"status":report["status"],"selecionadas":0},ensure_ascii=False),flush=True)
        return True
    try:
        urls=published_urls(uf)
        compiler=asn1tools.compile_files(str(SPEC/"assinatura.asn1"),codec="ber")
        with range_mod.RemoteZip(url=urls["bruto"]) as remote:
            with zipfile.ZipFile(remote) as archive:
                sections,_=file_index_uf(archive,uf)
                for row in selected:
                    key=(int(row["cod_municipio_tse"]),int(row["zona"]),int(row["secao"]))
                    slug="/".join(map(str,key))
                    item={
                        "municipio":row["municipio"],"zona":key[1],"secao":key[2],
                        "urna_prevista":row["urna_prevista"],"urna_efetivada":row["urna_efetivada"],
                        "encerramento_bweb":row["encerramento_original"],"status":"INCONCLUSIVO",
                    }
                    try:
                        files={name:archive.read(entry) for name,entry in sections[key].items()}
                        if not {"bu.dat","rdv.dat","imgbu.dat","log.jez","vota.vsc"}.issubset(files):
                            raise ValueError(f"Arquivos de seção incompletos: {list(files)}")
                        digests,_=signature_hashes(files["vota.vsc"],compiler)
                        checks=compare_hashes(files,digests)
                        required={"bu.dat","rdv.dat","imgbu.dat","log.jez"}
                        checked={name.rsplit("-",1)[-1]
                            for name,match in checks.items() if match=="HASH_OK"}
                        invalid={name:match for name,match in checks.items()
                            if match in ("HASH_DIVERGENTE","HASHES_DECLARADOS_DIVERGENTES","NOME_INVALIDO")}
                        item["hashes_conferidos"]=len(checked & required)
                        item["referencias_extras_no_vsc"]=sum(
                            match=="SEM_ARQUIVO_OU_AMBIGUO" for match in checks.values())
                        if invalid or not required.issubset(checked):
                            raise ValueError("Hash dos quatro arquivos obrigatórios não coincide com VSC")
                        stats,nlogs=inspect_log(files["log.jez"],row["urna_efetivada"])
                        item["eventos_log"]=stats
                        item["arquivos_logd"]=nlogs
                        before=stats.get("efetiva_eventos_antes_17h",0)
                        item["status"]=(
                            "URNA_EFETIVADA_ATIVA_ANTES_17H" if before>0
                            else "SEM_EVENTO_PRE17H_URNA_EFETIVADA_NOS_LOGS_PUBLICOS"
                        )
                    except Exception as exc:
                        item["erro"]=f"{type(exc).__name__}: {exc}"
                        item["status"]="INCONCLUSIVO"
                    report["secoes"][slug]=item
                    report["examinadas"]+=1
                    print(json.dumps({"uf":uf,"secao":slug,"resultado":item["status"],
                        "eventos_efetiva_antes17":item.get("eventos_log",{}).get("efetiva_eventos_antes_17h",0),
                        "erro":item.get("erro")},ensure_ascii=False),flush=True)
            report["range_bytes_lidos"]=remote.bytes_fetched
            report["range_requisicoes"]=remote.http_requests
    except Exception as exc:
        report["erros"].append(f"{type(exc).__name__}: {exc}")
    report["sintese"]=dict(Counter(x["status"] for x in report["secoes"].values()))
    report["status"]=(
        "CONCLUIDO" if report["examinadas"]==len(selected) and not report["erros"] 
        and "INCONCLUSIVO" not in report["sintese"] else "PARCIAL")
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"uf":uf,"status":report["status"],"selecionadas":len(selected),
                      "examinadas":report["examinadas"],"sintese":report["sintese"],
                      "erros":report["erros"]},ensure_ascii=False),flush=True)
    return report["status"]=="CONCLUIDO"

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--uf",required=True)
    p.add_argument("--csv",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    if not run(a.uf,a.csv,a.out):raise SystemExit(2)
