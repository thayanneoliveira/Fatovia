"""Auditoria integral MA 2026 2T com dados publicados, sem explorar infraestrutura.

Reconta RDVs por seção e confronta com BU CSV, total de eventos nos logs,
identidades da urna no CEFT, e SHA512 de BU/RDV/IMGBU/LOG declarados nos VSCs.
A verificação de assinaturas criptográficas e da cadeia de confiança NÃO integra
esta execução. Inconsistência não é equivalente a fraude.

O ZIP bruto (4.25GB) é baixado apenas uma vez em um runner temporário; nenhuma
sequência individual de voto é salva no relatório. Nenhum acesso autenticado.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import zipfile

from .ma_amostra_profunda import (
    BU_URL, FILES, SPEC, URL,
    decode_rdv, file_index, log_summary, signature_hashes, compare_hashes
)
from .proveniencia_ma import read_selected_rows
from .tse import csv_rows, download_zip, sha512_expected

MAX_BYTES = 5_000_000_000
PROGRESS_EVERY = 1000
EXPECTED_FILES = frozenset(("vota.vsc","bu.dat","rdv.dat","imgbu.dat","log.jez"))


def checked_reference(url, filename, directory):
    expected = sha512_expected(url+".sha512")
    dest=Path(directory)/filename
    actual,size=download_zip(url,dest)
    if actual!=expected:
        raise ValueError(f"SHA512 de referência não coincide: {url}")
    return dest, {"url":url,"sha512":actual,"bytes":size,"hash_conferido":True}


def bu_reference(path):
    result=defaultdict(Counter)
    attendance={}
    n=0
    for row in csv_rows(path):
        if row.get("NR_TURNO")!="2" or row.get("CD_CARGO_PERGUNTA")!="1":
            continue
        key=(int(row["CD_MUNICIPIO"]),int(row["NR_ZONA"]),int(row["NR_SECAO"]))
        code=str(int(row["NR_VOTAVEL"]))
        n_votes=int(row["QT_VOTOS"])
        if n_votes<0:raise ValueError("Contagem negativa")
        result[key][code]+=n_votes
        n+=1
        cur=int(row["QT_COMPARECIMENTO"])
        if key in attendance and attendance[key]!=cur:
            raise ValueError(f"Comparecimento inconsistente no BU {key}")
        attendance[key]=cur
    if not result:raise ValueError("Referência BU vazia")
    for k,v in result.items():
        if sum(v.values())!=attendance[k]:
            raise ValueError(f"BU inconsistente em {k}")
    return {k:{n:val for n,val in c.items() if val>0} for k,c in result.items()},attendance,n


def ceft_reference(path):
    result={}
    duplicates=[]
    for row in read_selected_rows(path,"ceft_"):
        key=(int(row["CD_MUNICIPIO"]),int(row["NR_ZONA"]),int(row["NR_SECAO"]))
        if key in result:
            duplicates.append(list(key))
            continue
        result[key]={col:row.get(col,"") for col in (
            "NR_URNA_ESPERADA","NR_URNA_EFETIVADA",
            "CD_CARGA_URNA_ESPERADA","CD_CARGA_URNA_EFETIVADA",
            "TP_DIVERGENCIA","DS_ORIGEM_VOTO")}
    if duplicates:
        raise ValueError(f"CEFT contém seções duplicadas: {duplicates[:10]}")
    return result


def stream_full_zip(url,dest,expected_sha=None):
    """Download único sequencial, limite de tamanho, verificação de ZIP e SHA512."""
    dest=Path(dest)
    hasher=hashlib.sha512()
    n=0
    req=Request(url,headers={"User-Agent":"FatoViaAudita/1.1 (dados abertos)"})
    with urlopen(req,timeout=180) as response, dest.open("wb") as output:
        if response.status!=200:raise ValueError(f"HTTP {response.status}")
        length=response.headers.get("Content-Length")
        if length and int(length)>MAX_BYTES:raise ValueError("ZIP acima do limite")
        while True:
            data=response.read(4*1024*1024)
            if not data:break
            n+=len(data)
            if n>MAX_BYTES:raise ValueError("Limite de download ultrapassado")
            hasher.update(data)
            output.write(data)
    if not zipfile.is_zipfile(dest):
        raise ValueError("ZIP bruto inválido")
    if length and n!=int(length):
        raise ValueError(f"Download incompleto: {n}/{length} bytes")
    h=hasher.hexdigest()
    if expected_sha and h!=expected_sha:
        raise ValueError("SHA512 do pacote bruto difere do hash oficial")
    return {"url":url,"sha512_calculado":h,"bytes":n,
            "sha512_publicado_disponivel":expected_sha is not None,
            "sha512_conferido":h==expected_sha if expected_sha else None}


def audit_section(archive, key, entries, bu_counts, expected_turnout, ceft, rdvc, sigc):
    """Diagnóstico por seção; nunca extrai votos individuais no JSON."""
    rec={"secao":list(key),"resultados":{},
         "alertas":[],"limitacoes":[]}
    if set(entries)!=EXPECTED_FILES:
        rec["alertas"].append("ARQUIVOS_DA_SECAO_AUSENTES_OU_EXTRAS")
        rec["tipos_encontrados"]=sorted(entries)
        return rec
    if key not in bu_counts:
        rec["alertas"].append("SECAO_SEM_BU_PUBLICADO")
        return rec
    if key not in ceft:
        rec["alertas"].append("SECAO_SEM_CEFT")
        return rec

    # leitura das cinco entradas da seção no único ZIP local
    files={kind:archive.read(info) for kind,info in entries.items()}
    hashes,info=signature_hashes(files["vota.vsc"],sigc)
    checks=compare_hashes(files,hashes)
    required={"bu.dat","rdv.dat","imgbu.dat","log.jez"}
    checked_keys={file.rsplit("-",1)[-1] for file,status in checks.items() if status=="HASH_OK"}
    hash_bad={file:status for file,status in checks.items()
              if status in ("HASH_DIVERGENTE","HASHES_DECLARADOS_DIVERGENTES","NOME_INVALIDO")}
    # Campos não publicados dentro do pacote não são falhas de integridade
    if hash_bad:rec["alertas"].append("HASH_SHA512_DIVERGENTE")
    if not required.issubset(checked_keys):
        rec["alertas"].append("HASH_DOS_QUATRO_ARQUIVOS_NAO_CONFERIDO")
    rec["resultados"]["hashes_sha512"]= {
        "arquivos_presentes_conferidos":len(checked_keys&required),
        "hashes_diferentes":hash_bad,
        "referencias_a_arquivos_nao_presentes":sum(1 for v in checks.values()
                                                   if v=="SEM_ARQUIVO_OU_AMBIGUO"),
        "assinatura_digital_criptograficamente_validada":False,
    }
    try:
        rdv=decode_rdv(files["rdv.dat"],rdvc)
        if tuple(rdv["secao_interna"])!=key:
            rec["alertas"].append("RDV_IDENTIFICADOR_DE_SECAO_DIVERGENTE")
        if rdv["fase"]!="oficial":
            rec["alertas"].append("RDV_FASE_NAO_OFICIAL")
        counts={str(k):int(v) for k,v in rdv["votos"].items() if int(v)>0}
        rdv_bu_equal=counts==bu_counts[key]
        if not rdv_bu_equal:
            rec["alertas"].append("RDV_DIFERENTE_DO_BU")
            rec["resultados"]["diferencas_rdv_bu"]={
                v:[counts.get(v,0),bu_counts[key].get(v,0)]
                for v in sorted(set(counts)|set(bu_counts[key]))
                if counts.get(v,0)!=bu_counts[key].get(v,0)}
        if rdv["registros_presidente"]!=expected_turnout[key]:
            rec["alertas"].append("RDV_REGISTROS_DIFERENTE_COMPARECIMENTO")
        rec["resultados"]["rdv"]={
            "registros":rdv["registros_presidente"],
            "comparecimento_bu":expected_turnout[key],
            "identidade_secao_confere":tuple(rdv["secao_interna"])==key,
            "contagens_confere_bu":rdv_bu_equal,
        }
    except Exception as exc:
        rdv=None
        rec["alertas"].append("FALHA_AO_DECODIFICAR_RDV")
        rec["resultados"]["erro_rdv"]=f"{type(exc).__name__}: {exc}"

    try:
        logs=log_summary(files["log.jez"])
        is_sa="Urna Eletrônica" not in ceft[key]["DS_ORIGEM_VOTO"]
        log_equal=logs["total_eventos_voto_25_10"]==expected_turnout[key]
        if not is_sa and not log_equal:
            rec["alertas"].append("LOG_EVENTOS_VOTO_DIFERENTE_COMPARECIMENTO")
        rec["resultados"]["log"]={
            "aplicavel":not is_sa,
            "eventos_voto_25_10":logs["total_eventos_voto_25_10"],
            "comparecimento_bu":expected_turnout[key],
            "eventos_igual_comparecimento":log_equal if not is_sa else None,
            "qtd_arquivos_logd":logs["logs_internos"],
            "urnas_eventos":logs["urnas_com_eventos_voto_25_10"],
            "eventos_em_outras_datas":{d:v for d,v in logs["eventos_voto_por_data"].items()
                                       if d!="25/10/2026"},
        }
        if is_sa:
            rec["limitacoes"].append("LOG_DE_URNA_NAO_APLICAVEL_A_APURACAO_ESPECIAL")
    except Exception as exc:
        logs=None
        rec["alertas"].append("FALHA_AO_PROCESSAR_LOG")
        rec["resultados"]["erro_log"]=f"{type(exc).__name__}: {exc}"

    try:
        effective=ceft[key]
        reported=rdv.get("numero_interno_urna") if rdv else None
        actual=effective["NR_URNA_EFETIVADA"]
        rdv_matches=reported is not None and actual and int(reported)==int(actual)
        load_matches=rdv and str(rdv.get("codigo_carga_urna"))==effective["CD_CARGA_URNA_EFETIVADA"]
        log_matches=(actual and logs and int(actual) in logs["urnas_com_eventos_voto_25_10"])
        if not rdv_matches:rec["alertas"].append("RDV_URNA_DIFERENTE_CEFT")
        if not load_matches:rec["alertas"].append("RDV_CARGA_DIFERENTE_CEFT")
        if logs and not log_matches and "Urna Eletrônica" in effective["DS_ORIGEM_VOTO"]:
            rec["alertas"].append("CEFT_URNA_AUSENTE_DOS_LOGS")
        rec["resultados"]["proveniencia"]={
            "urna_prevista_diferente_da_efetivada":effective["NR_URNA_ESPERADA"]!=actual,
            "tipo_divergencia":effective["TP_DIVERGENCIA"],
            "identidade_rdv_confere_ceft":bool(rdv_matches),
            "carga_rdv_confere_ceft":bool(load_matches),
            "urna_efetivada_no_log":bool(log_matches) if logs else None,
            "origem":effective["DS_ORIGEM_VOTO"],
        }
    except Exception as exc:
        rec["alertas"].append("FALHA_CRUZAMENTO_PROVENIENCIA")
        rec["resultados"]["erro_proveniencia"]=f"{type(exc).__name__}: {exc}"

    return rec


def main():
    import asn1tools
    import argparse
    cli=argparse.ArgumentParser()
    cli.add_argument("--out",default="work/ma-integral")
    cli.add_argument("--max-sections",type=int,default=0,
                     help="0 = TODAS as seções; outro número serve SOMENTE para testes")
    args=cli.parse_args()
    outdir=Path(args.out)
    outdir.mkdir(parents=True,exist_ok=True)
    report={
        "projeto":"FATOVIA AUDITA","escopo":"Maranhão, segundo turno 2026, Presidente",
        "gerado_utc":datetime.now(timezone.utc).isoformat(),
        "status":"INCONCLUSIVO","metodo":"recontagem RDV por seção, evento de voto no log, proveniência CEFT e SHA512 declarado em VSC",
        "assinatura_criptografica_verificada":False,
        "limitacoes":[
            "Não valida criptograficamente a assinatura da urna, certificado ou cadeia de confiança.",
            "Dados das seções estão no sistema do TSE; concordância não prova registro fiel da intenção do eleitor.",
            "Eventos em logs podem depender de recuperação de arquivos e contingência operacional.",
            "Mudança de urna e campos não preenchidos não são prova de fraude.",
            "Arquivos de transmissões rejeitadas ou pendentes podem não estar no pacote totalizado."
        ],
        "fontes":{},"cobertura":{},"resultado_por_secao":{},
        "ocorrencias":{},"ocorrencias_amostra":{}
    }
    with tempfile.TemporaryDirectory(prefix="fatovia-ma-integral-") as tmp:
        bu_path, report["fontes"]["bu"]=checked_reference(BU_URL,"bu.zip",tmp)
        ceft_path, report["fontes"]["ceft"]=checked_reference(FILES["efetivada_26"],"ceft.zip",tmp)
        bu,attendance,bu_rows=bu_reference(bu_path)
        ceft=ceft_reference(ceft_path)
        print(f"Referências verificadas: BU={len(bu)} seções, CEFT={len(ceft)} seções, linhas BU={bu_rows}",flush=True)
        digest=None
        try:
            digest=sha512_expected(URL+".sha512")
            print("Hash SHA512 do arquivo bruto disponível no TSE",flush=True)
        except (ValueError,HTTPError,OSError,RuntimeError) as exc:
            print(f"Hash externo do ZIP bruto não disponível: {type(exc).__name__}: {exc}",flush=True)
            report["limitacoes"].append("Hash externo do ZIP bruto não foi obtido; hashes por arquivo via VSC são verificados individualmente.")
        raw_path=Path(tmp)/"arqurna_ma.zip"
        report["fontes"]["arquivo_bruto"]=stream_full_zip(URL,raw_path,digest)
        print(f"ZIP bruto íntegro e baixado: {report['fontes']['arquivo_bruto']['bytes']} bytes",flush=True)
        rdvc=asn1tools.compile_files(str(SPEC/"rdv.asn1"),codec="ber")
        sigc=asn1tools.compile_files(str(SPEC/"assinatura.asn1"),codec="ber")
        with zipfile.ZipFile(raw_path) as archive:
            sections,index=file_index(archive)
            allkeys=set(bu)|set(ceft)|set(sections)
            diffs={
                "bu_sem_ceft":len(set(bu)-set(ceft)),
                "bu_sem_pacote_bruto":len(set(bu)-set(sections)),
                "ceft_sem_bu":len(set(ceft)-set(bu)),
                "pacote_bruto_sem_bu":len(set(sections)-set(bu)),
            }
            report["cobertura"]={"secoes_bu":len(bu),"secoes_ceft":len(ceft),
                "secoes_pacote_bruto":len(sections),"secoes_distintas":len(allkeys),
                "chaves_sem_correspondencia":diffs,
                "inventario":index,"secoes_processadas":0,"secoes_alertadas":0}
            issues=Counter()
            samples=defaultdict(list)
            tests=Counter()
            errors=0
            for i,key in enumerate(sorted(allkeys),1):
                if args.max_sections and i>args.max_sections:break
                try:
                    rec=audit_section(archive,key,sections.get(key,{}),bu,attendance,ceft,rdvc,sigc)
                except Exception as exc:
                    rec={"secao":list(key),"alertas":["EXCECAO_NAO_TRATADA"],
                         "erro":f"{type(exc).__name__}: {exc}"}
                    errors+=1
                for typ in rec.get("alertas",[]):
                    issues[typ]+=1
                    if len(samples[typ])<30:samples[typ].append(list(key))
                result=rec.get("resultados",{})
                h=result.get("hashes_sha512",{})
                tests["arquivos_sha512_conferidos"]+=h.get("arquivos_presentes_conferidos",0)
                tests["arquivos_sha512_divergentes"]+=len(h.get("hashes_diferentes",{}))
                if result.get("rdv",{}).get("contagens_confere_bu") is True:tests["rdv_bu_ok"]+=1
                if result.get("rdv",{}).get("identidade_secao_confere") is True:tests["rdv_secao_ok"]+=1
                if result.get("log",{}).get("eventos_igual_comparecimento") is True:tests["log_bu_ok"]+=1
                if result.get("log",{}).get("aplicavel") is False:tests["log_nao_aplicavel"]+=1
                if result.get("proveniencia",{}).get("identidade_rdv_confere_ceft") is True:
                    tests["rdv_urna_ceft_ok"]+=1
                if result.get("proveniencia",{}).get("carga_rdv_confere_ceft") is True:
                    tests["rdv_carga_ceft_ok"]+=1
                if result.get("proveniencia",{}).get("urna_prevista_diferente_da_efetivada") is True:
                    tests["urna_esperada_diferente_efetivada"]+=1
                if result.get("proveniencia",{}).get("urna_efetivada_no_log") is True:
                    tests["urna_ceft_log_ok"]+=1
                if rec.get("alertas"):
                    report["resultado_por_secao"]["/".join(map(str,key))]=rec
                report["cobertura"]["secoes_processadas"]=i
                report["cobertura"]["secoes_alertadas"]=sum(1 for _ in report["resultado_por_secao"])
                if i%PROGRESS_EVERY==0:
                    print(f"Progresso: {i}/{len(allkeys)} seções; alertas={sum(issues.values())}; "
                          f"RDV BU ok={tests['rdv_bu_ok']} | logs ok={tests['log_bu_ok']}",flush=True)
            report["verificacoes"]=dict(tests)
            report["ocorrencias"]=dict(issues)
            report["ocorrencias_amostra"]=dict(samples)
            report["falhas_nao_tratadas"]=errors
            fully_processed=report["cobertura"]["secoes_processadas"]==len(allkeys)
            coverage_ok=all(n==0 for n in diffs.values()) and len(bu)==len(ceft)==len(sections)
            if not fully_processed or not coverage_ok:
                report["status"]="INCONCLUSIVO"
            elif issues:
                report["status"]="ALERTAS_TECNICOS_REQUEREM_ANALISE"
            else:
                report["status"]="CONFERENCIA_INTERNA_CONSISTENTE_COM_RESSALVAS"
    final=outdir/"ma-2026-2t-integral.json"
    final.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":report["status"],"cobertura":report["cobertura"],
                      "verificacoes":report.get("verificacoes"),"ocorrencias":report.get("ocorrencias")},
                     ensure_ascii=False,default=str),flush=True)
    print("Saída:",final,flush=True)
    if report["status"]=="INCONCLUSIVO":raise SystemExit(2)

if __name__=="__main__":
    main()
