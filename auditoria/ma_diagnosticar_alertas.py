"""Diagnóstico focal de alertas do FATOVIA MA: somente arquivos públicos.

Reúne dados técnicos das seções sem expor votos individuais, ordem ou timestamps
de eventos individuais de votação. Este script NÃO verifica intenção do eleitor.
"""
from __future__ import annotations
import json,zipfile,io
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from .ma_amostra_profunda import (
    sample_bu_counts,sample_ceft,decode_rdv,log_summary,file_index,SPEC)
from .ma_arqurna_range import RemoteZip

FOCO=((7005,12,28),(7005,12,61),(7005,12,176),
      (8893,47,609),(7536,26,88),(9210,1,124),(7005,12,21))

def inspect_event_log(raw):
    nested=[]
    def extract(data,depth):
        if depth>3:raise ValueError("Log aninhado demais")
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                if info.is_dir():continue
                if info.file_size>20_000_000:raise ValueError("Log acima do limite")
                part=z.read(info)
                if info.filename.lower().endswith(".jez"):
                    extract(part,depth+1)
                elif info.filename.lower().endswith("logd.dat"):
                    text=part.decode("latin-1")
                    votes=Counter()
                    phases=Counter()
                    apps=Counter()
                    keys=set()
                    for line in text.splitlines():
                        fields=line.split("\t")
                        if len(fields)<5:continue
                        time,level,serial,app,event=fields[:5]
                        day=time[:10]
                        keys.add(serial)
                        if "O voto do eleitor foi computado" in event and app=="VOTA":
                            votes[day]+=1
                        if day=="25/10/2026":
                            apps[app]+=1
                            t=event.casefold()
                            if "pronta para receber votos" in t:phases["pronta"]+=1
                            if "início do encerramento" in t or "inicio do encerramento" in t: phases["encerramento"]+=1
                            if "erro" in t or "falha" in t:phases["erro_ou_falha"]+=1
                            if "recuper" in t or "conting" in t or "substitu" in t:phases["recuperacao_ou_troca"]+=1
                    nested.append({"nome_arq_interno":info.filename,
                                   "eventos_voto_por_dia":dict(votes),
                                   "etapas_e_eventos":dict(phases),
                                   "aplicativos_eventos_25_10":dict(apps),
                                   "id_urna_distintos":sorted(keys)[:12]})
    extract(raw,0)
    return nested

def main():
    import asn1tools
    compiler=asn1tools.compile_files(str(SPEC/"rdv.asn1"),codec="ber")
    # sample_bu_counts usa ALVOS constante de 6 - obter BU focal diretamente
    from .tse import csv_rows,download_zip
    from .ma_amostra_profunda import BU_URL
    from tempfile import TemporaryDirectory
    bu={}
    with TemporaryDirectory() as tmp:
        path=Path(tmp)/"bu.zip"
        download_zip(BU_URL,path)
        for row in csv_rows(path):
            if row.get("NR_TURNO")!="2" or row.get("CD_CARGO_PERGUNTA")!="1":
                continue
            key=(int(row["CD_MUNICIPIO"]),int(row["NR_ZONA"]),int(row["NR_SECAO"]))
            if key in FOCO:
                rec=bu.setdefault(key,{"comparecimento":int(row["QT_COMPARECIMENTO"]),"votos":{}})
                if int(row["QT_VOTOS"])>0:
                    rec["votos"][row["NR_VOTAVEL"]]=int(row["QT_VOTOS"])
    from .proveniencia_ma import FILES,read_selected_rows
    from .tse import sha512_expected
    ceft={}
    comprimento_ceft=Counter()
    ceft_secoes_com_carga_menor_24=0
    with TemporaryDirectory() as tmp:
        path=Path(tmp)/"ceft.zip"
        hashval,size=download_zip(FILES["efetivada_26"],path)
        if sha512_expected(FILES["efetivada_26"]+".sha512")!=hashval:
            raise ValueError("hash CEFT diferente")
        for row in read_selected_rows(path,"ceft_"):
            key=(int(row["CD_MUNICIPIO"]),int(row["NR_ZONA"]),int(row["NR_SECAO"]))
            codigo=row.get("CD_CARGA_URNA_EFETIVADA","")
            comprimento_ceft[len(codigo)]+=1
            if len(codigo)<24:ceft_secoes_com_carga_menor_24+=1
            if key in FOCO:ceft[key]=row
    out={"utc":datetime.now(timezone.utc).isoformat(),
         "fontes":"BU, CEFT, RDV, logs publicados pelo TSE",
         "distribuicao_comprimentos_codigo_carga_ceft":dict(comprimento_ceft),
         "ceft_secoes_com_codigo_carga_menor_24":ceft_secoes_com_carga_menor_24,
         "amostra_1775_alarmes_codigo_carga":"Verificar se total de códigos CEFT com menos de 24 dígitos coincide com 1775 alertas",
         "secoes":{}}
    with RemoteZip() as remote:
        with zipfile.ZipFile(remote) as archive:
            idx,inv=file_index(archive)
            for key in FOCO:
                section={"secao":list(key)}
                entries=idx.get(key)
                if not entries:
                    section["erro"]="não há seção no pacote bruto"
                    out["secoes"]["/".join(map(str,key))]=section
                    continue
                rdv=decode_rdv(archive.read(entries["rdv.dat"]),compiler)
                logs=log_summary(archive.read(entries["log.jez"]))
                ceft_row=ceft[key]
                code_rdv=rdv.get("codigo_carga_urna")
                code_ceft=ceft_row.get("CD_CARGA_URNA_EFETIVADA")
                section["carga"]={
                    "valor_no_rdv":code_rdv,
                    "tipo_do_valor_rdv":type(code_rdv).__name__,
                    "valor_no_ceft":code_ceft,
                    "comprimento_rdv":len(str(code_rdv)),
                    "comprimento_ceft":len(str(code_ceft)),
                    "coincide_exatamente":str(code_rdv)==str(code_ceft),
                    "mesmo_apos_remover_zeros_iniciais":str(code_rdv).lstrip("0")==str(code_ceft).lstrip("0"),
                    "mesmo_prefixo_12":str(code_rdv)[:12]==str(code_ceft)[:12],
                    "mesmos_ultimos_12":str(code_rdv)[-12:]==str(code_ceft)[-12:],
                    "carga_esperada":ceft_row.get("CD_CARGA_URNA_ESPERADA"),
                    "urna_esperada":ceft_row.get("NR_URNA_ESPERADA"),
                    "urna_efetivada":ceft_row.get("NR_URNA_EFETIVADA"),
                    "codigo_tipo_divergencia":ceft_row.get("TP_DIVERGENCIA"),
                    "numero_urna_rdv":rdv.get("numero_interno_urna"),
                }
                section["votos"]={
                    "comparecimento_bu":bu[key]["comparecimento"],
                    "votos_rdv_presidente":rdv["votos"],
                    "votos_bu_presidente":bu[key]["votos"],
                    "eventos_de_voto_log_25_10":logs["total_eventos_voto_25_10"],
                    "logs_embutidos":logs["logs_internos"],
                    "eventos_voto_por_data":logs["eventos_voto_por_data"],
                    "id_urnas_logs":logs["urnas_com_eventos_voto_25_10"],
                }
                section["log_detalhe_agregado"]=inspect_event_log(archive.read(entries["log.jez"]))
                out["secoes"]["/".join(map(str,key))]=section
            out["bytes_baixados_por_range"]=remote.bytes_fetched
    dest=Path("work/aprofundada/ma_diagnostico_alertas.json")
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    # sem dados individualizados, apenas contagens e informações de carga
    print(json.dumps(out,indent=2,ensure_ascii=False),flush=True)
if __name__=="__main__":main()
