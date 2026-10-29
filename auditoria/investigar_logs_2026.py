"""FATOVIA AUDITA: perícia técnica independente sobre 6 divergências de logs.

Somente arquivos TOTALIZADOS publicados pelo TSE; sem autenticação, varredura
de segurança, dados pessoais, ordem de votos, nem timestamps individuais.
O teste deve diferenciar falta de trilha disponível de diferença na apuração.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import hashlib
import io
import json
import re
import zipfile

from .brasil_2026 import published_urls, file_index_uf
from .ma_arqurna_range import RemoteZip
from .ma_amostra_profunda import SPEC, decode_rdv, signature_hashes, compare_hashes, log_summary
from .ma_integral import checked_reference, bu_reference, ceft_reference

ALVOS={
    "BA":[(34711,21,178),(35653,173,235)],
    "MA":[(8893,47,609)],
    "PB":[(21750,2,254)],
    "PI":[(11533,3,216)],
    "RS":[(89060,17,191)],
}
# Exame técnico adicional de rastreabilidade, sem confundir com o evento de voto.
AMOSTRA_URNA={
    "BA":[(38458,87,193)],
    "MG":[(40690,16,264),(41882,320,185)],
    "PA":[(4278,98,294),(5290,36,441)],
    "PB":[(19933,3,259)],
    "PE":[(24791,90,24)],
    "RJ":[(58971,68,154)],
    "RS":[(84913,138,14)],
    "SP":[(62936,344,131),(66397,399,48)],
}
VOTE_MARK="O voto do eleitor foi computado"
UNSAFE_EVENT=re.compile(r"(eleitor|documento|titulo|título|cpf|digital|nascimento)",re.I)
INDICATORS={
    "interrupcao":("interrup","deslig","reinic","trav"),
    "troca_contingencia":("conting","substit","nova urna","troca de urna"),
    "recuperacao":("recuper","restaur","mídia","midia","flash","backup"),
    "incidente":("falha","erro","inconsistência","inconsistencia"),
    "encerramento":("encerr","finaliz","geração de arquivo","geracao de arquivo"),
}


def log_entries(raw):
    """Ler somente logd.dat aninhados; limitar tamanho de descompressão."""
    texts=[]
    def collect(data,depth):
        if depth>3:raise ValueError("ZIP log aninhado acima do limite")
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                if info.is_dir():continue
                if info.file_size>20*1024*1024:raise ValueError("Log individual muito grande")
                part=z.read(info)
                name=info.filename.lower()
                if name.endswith(".jez"):
                    collect(part,depth+1)
                elif name.endswith("logd.dat"):
                    texts.append(part.decode("latin-1",errors="strict"))
    collect(raw,0)
    if not texts:raise ValueError("Arquivo logd.dat não encontrado")
    return texts


def analyze_log(raw):
    texts=log_entries(raw)
    counted=Counter()
    by_copy=[]
    indicators=Counter()
    urn_voting=defaultdict(Counter)
    hours=Counter()
    message_classes=Counter()
    ignored=Counter()
    # O conjunto união elimina cópias exatas de linhas, preservando
    # a maior multiplicidade por arquivo (mesmo método do auditor integral).
    union=Counter()
    for idx,t in enumerate(texts):
        c=Counter(t.splitlines())
        events=Counter()
        serials=set()
        for line,quantity in c.items():
            fields=line.split("\t")
            if len(fields)<5:continue
            when,level,serial,app,msg=fields[:5]
            if VOTE_MARK in msg and app=="VOTA":
                events[when[:10]]+=quantity
                serials.add(serial)
        by_copy.append({
            "indice_log":idx+1,
            "tamanho_descomprimido_bytes":len(t.encode("latin-1")),
            "sha256_log_original":hashlib.sha256(t.encode("latin-1")).hexdigest(),
            "eventos_voto_por_dia":dict(events),
            "urnas_com_eventos":sorted(serials),
        })
        for line,quantity in c.items():
            union[line]=max(union[line],quantity)
    for line,quantity in union.items():
        fields=line.split("\t")
        if len(fields)<5:
            ignored["campos_insuficientes"]+=quantity
            continue
        when,level,serial,app,msg=fields[:5]
        day=when[:10]
        lower=msg.casefold()
        if "voto" in lower and ("computad" in lower or "registrad" in lower):
            message_classes["mensagens_voto_ou_registro"]+=quantity
        if VOTE_MARK in msg and app=="VOTA":
            counted[day]+=quantity
            urn_voting[day][serial]+=quantity
            if day=="25/10/2026":
                # Hora agregada, nunca hora por voto individual.
                hour=when[11:13]
                hours[hour]+=quantity
        if day=="25/10/2026":
            for category,terms in INDICATORS.items():
                if any(term in lower for term in terms):
                    indicators[category]+=quantity
        if "voto do eleitor" in lower and app!="VOTA":
            ignored["indicador_voto_em_outro_aplicativo"]+=quantity
    expected=log_summary(raw)
    independent=counted["25/10/2026"]
    if independent!=expected["total_eventos_voto_25_10"]:
        raise ValueError("Contadores independentes discordam do auditor original")
    return {
        "qtd_logs_internos":len(texts),
        "contagem_por_log":by_copy,
        "eventos_voto_por_dia_uniao":dict(counted),
        "eventos_voto_por_urna_25_10":dict(urn_voting["25/10/2026"]),
        "eventos_por_hora_25_10":dict(sorted(hours.items())),
        "indicadores_de_eventos_25_10":dict(indicators),
        "mensagens_candidatas":dict(message_classes),
        "linhas_sem_formato_padrao":dict(ignored),
        "observacao":"Eventos agregados, sem votos individuais, timestamps, identificação de pessoas nem ordem de registro.",
    }


def process_uf(uf,out):
    import asn1tools
    targets=list(dict.fromkeys(ALVOS.get(uf,[])+AMOSTRA_URNA.get(uf,[])))
    result={"uf":uf,"gerado_utc":datetime.now(timezone.utc).isoformat(),
            "metodo":"Reconferência seletiva de logs aninhados + BU/RDV + CEFT e hashes declarados no VSC",
            "hipoteses":["Log anterior à contingência não publicado",
                         "Registro final não persistido no log publicado",
                         "Cópias/duplicações, formato não interpretado ou erro de leitura",
                         "Inconsistência de trilha a explicar"],
            "assinatura_digital_criptograficamente_validada":False,
            "secoes":{},"origens":{}}
    out=Path(out)
    out.parent.mkdir(parents=True,exist_ok=True)
    try:
        urls=published_urls(uf)
        result["origens"]=urls
        with TemporaryDirectory() as temp:
            bu_path,_=checked_reference(urls["bu"],"bu.zip",temp)
            ceft_path,_=checked_reference(urls["ceft"],"ceft.zip",temp)
            bu,attendance,_=bu_reference(bu_path)
            ceft=ceft_reference(ceft_path)
            compiler=asn1tools.compile_files(str(SPEC/"rdv.asn1"),codec="ber")
            sigc=asn1tools.compile_files(str(SPEC/"assinatura.asn1"),codec="ber")
            with RemoteZip(url=urls["bruto"]) as remote:
                with zipfile.ZipFile(remote) as archive:
                    sections,inventory=file_index_uf(archive,uf)
                    for key in targets:
                        tag="/".join(map(str,key))
                        rec={"secao":list(key),
                             "grupo":"log_divergente" if key in ALVOS.get(uf,[]) else "urna_no_log",
                             "situacao":"INCONCLUSIVO"}
                        try:
                            if key not in bu or key not in ceft or key not in sections:
                                raise ValueError("Seção não encontrada em todas as fontes")
                            files={kind:archive.read(info) for kind,info in sections[key].items()}
                            if not {"log.jez","rdv.dat","vota.vsc","bu.dat","imgbu.dat"}.issubset(files):
                                raise ValueError(f"Arquivos faltando: {sorted(files)}")
                            digests,_=signature_hashes(files["vota.vsc"],sigc)
                            checks=compare_hashes(files,digests)
                            rdv=decode_rdv(files["rdv.dat"],compiler)
                            voter_counts={str(k):int(v) for k,v in rdv["votos"].items() if int(v)>0}
                            log=analyze_log(files["log.jez"])
                            bu_counts=bu[key]
                            comparecimento=attendance[key]
                            log_count=log["eventos_voto_por_dia_uniao"].get("25/10/2026",0)
                            rec["dados"]={
                                "comparecimento_bu":comparecimento,
                                "total_rdv_presidente":rdv["registros_presidente"],
                                "rdv_igual_bu":voter_counts==bu_counts,
                                "rdv_identidade_secao_confere":tuple(rdv["secao_interna"])==key,
                                "urna_rdv":rdv.get("numero_interno_urna"),
                                "urna_esperada_ceft":ceft[key].get("NR_URNA_ESPERADA"),
                                "urna_efetivada_ceft":ceft[key].get("NR_URNA_EFETIVADA"),
                                "tipo_divergencia_ceft":ceft[key].get("TP_DIVERGENCIA"),
                                "eventos_no_log":log_count,
                                "diferenca_bu_menos_log":comparecimento-log_count,
                                "sha512_quatro_arquivos_conferem":sum(
                                    1 for value in checks.values() if value=="HASH_OK")==4,
                                "log":log,
                            }
                            rec["situacao"]=("LOG_CONFERE" if log_count==comparecimento else
                                             "LACUNA_DE_EVENTOS_NOS_LOGS_PUBLICADOS")
                        except Exception as exc:
                            rec["situacao"]="ERRO_PROCESSAMENTO"
                            rec["erro"]=f"{type(exc).__name__}: {exc}"
                        result["secoes"][tag]=rec
                        print(json.dumps({"uf":uf,"secao":tag,
                            "situacao":rec["situacao"],
                            "diferenca":rec.get("dados",{}).get("diferenca_bu_menos_log"),
                            "copias":rec.get("dados",{}).get("log",{}).get("qtd_logs_internos"),
                            "erro":rec.get("erro")},ensure_ascii=False),flush=True)
                result["requisicoes_http_range"]=remote.http_requests
                result["bytes_transferidos_http_range"]=remote.bytes_fetched
    except Exception as exc:
        result["erro_uf"]=f"{type(exc).__name__}: {exc}"
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"uf":uf,
                      "secoes":len(result["secoes"]),
                      "erro":result.get("erro_uf"),
                      "situacoes":dict(Counter(rec["situacao"] for rec in result["secoes"].values()))},
                     ensure_ascii=False),flush=True)
    return not result.get("erro_uf") and not any(
        rec["situacao"]=="ERRO_PROCESSAMENTO" for rec in result["secoes"].values())


def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--uf",required=True,choices=sorted(set(ALVOS)|set(AMOSTRA_URNA)))
    cli.add_argument("--out",required=True)
    args=cli.parse_args()
    if not process_uf(args.uf,args.out):
        raise SystemExit(2)

if __name__=="__main__":
    main()
