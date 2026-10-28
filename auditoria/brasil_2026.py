"""FATOVIA AUDITA 2026, 2º turno. Verificação por UF de dados públicos TSE.

Obtém as referências reais do catálogo do TSE, valida URLs e SHA512 publicados,
e confronta, seção a seção, RDV/BU, logs, CEFT e SHA512 listado no arquivo VSC.
Os VSCs NÃO são validados criptograficamente; a cadeia de confiança não é checada.
Somente arquivos públicos totalizados, sem autenticação ou consulta a endpoints
administrativos. Relatórios não guardam registros individuais de voto.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from datetime import datetime,timezone
from html.parser import HTMLParser
import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import Request,urlopen
from urllib.parse import urlparse
import zipfile

from . import ma_integral as engine
from . import ma_arqurna_range as ranged
from .tse import UFS, fetch,sha512_expected
from .ma_amostra_profunda import SPEC

TSE="https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/"
DATASETS={
    "bu":"https://dadosabertos.tse.jus.br/dataset/resultados-2026-boletim-de-urna",
    "ceft":"https://dadosabertos.tse.jus.br/dataset/resultados-2026-correspondencias-esperadas-e-efetivadas-2-turno",
    "bruto":"https://dadosabertos.tse.jus.br/dataset/resultados-2026-arquivos-transmitidos-para-totalizacao",
}
MAX_LOCAL_ZIP=5_000_000_000
MAX_RANGE_BYTES=55_000_000_000

class TSELinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls=set()
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            href=dict(attrs).get("href","")
            if href.startswith(TSE):
                self.urls.add(href)


def published_urls(uf):
    """Seleciona arquivos listados NAS PÁGINAS do TSE, nunca um filename suposto."""
    if uf not in UFS:
        raise ValueError(f"UF inválida: {uf}")
    candidates={}
    patterns={
        "bu":rf"{re.escape(TSE)}buweb/bweb_2t_{uf}_\d+\.zip",
        "ceft":rf"{re.escape(TSE)}correspefet/CEFT_2t_{uf}_\d+\.zip",
    }
    for kind,rx in patterns.items():
        doc=fetch(DATASETS[kind],max_bytes=4_000_000).decode("utf-8")
        parser=TSELinks()
        parser.feed(doc)
        matches=sorted(url for url in parser.urls if re.fullmatch(rx,url))
        if len(matches)!=1:
            raise ValueError(f"{uf}: {kind} requer exatamente um arquivo no catálogo; encontrados={len(matches)}")
        candidates[kind]=matches[0]
    # URL de segundo turno com nome padronizado, verificada antes de abrir.
    url=TSE+f"arqurnatot/bu_imgbu_logjez_rdv_vscmr_2026_2t_{uf}.zip"
    with urlopen(Request(url,method="HEAD",
                         headers={"User-Agent":"FatoViaAudita/2.0 (dados públicos)"}),timeout=45) as response:
        if response.status!=200 or not response.headers.get("Content-Length"):
            raise ValueError(f"Pacote bruto não disponível para {uf}")
        size=int(response.headers["Content-Length"])
    if size<=0:
        raise ValueError("Tamanho de pacote bruto inválido")
    candidates["bruto"]=url
    candidates["bruto_bytes"]=size
    return candidates


def file_index_uf(archive,uf):
    """Confere nomes e unicidade por município/zona/seção no padrão do TSE."""
    pattern=re.compile(rf"^o\d{{5}}{uf.casefold()}(\d{{5}})(\d{{4}})(\d{{4}})-([^/]+)$",re.I)
    sections=defaultdict(dict)
    unexpected=[]
    duplicates=[]
    for info in archive.infolist():
        if info.is_dir():continue
        match=pattern.fullmatch(info.filename)
        if not match:
            if len(unexpected)<12:unexpected.append(info.filename)
            continue
        key=tuple(int(match.group(i)) for i in (1,2,3))
        kind=match.group(4).lower()
        if kind in sections[key]:
            duplicates.append((key,kind))
        else:
            sections[key][kind]=info
    counts=Counter(kind for row in sections.values() for kind in row)
    bad=[list(key) for key,items in sections.items()
         if set(items)!=engine.EXPECTED_FILES]
    summary={"secoes_com_arquivos":len(sections),
             "tipos":dict(counts),
             "secoes_com_tipos_incompletos":len(bad),
             "amostra_tipos_incompletos":bad[:20],
             "arquivos_duplicados":len(duplicates),
             "amostra_duplicados":[[list(k),v] for k,v in duplicates[:20]],
             "arquivos_fora_padrao_amostra":unexpected}
    return sections,summary


def check_brutal_zip(url,known_size,directory):
    """Escolhe download local ou leitura HTTP Range evitando estouro de disco."""
    if known_size<=MAX_LOCAL_ZIP:
        p=Path(directory)/"bruto.zip"
        meta=engine.stream_full_zip(url,p,None)
        return p,meta,False
    # O arquivo pode exceder capacidade efêmera de disco do GitHub Actions.
    # HTTP Range sem materialização do ZIP inteiro.
    ranged.MAX_BYTES_TRANSFERRED=MAX_RANGE_BYTES
    ranged.MAX_BLOCKS=24
    obj=ranged.RemoteZip(url=url)
    if obj.size!=known_size:
        raise ValueError("Arquivo remoto mudou de tamanho desde HEAD")
    return obj,{"url":url,"bytes_remotos":obj.size,
                "metodo":"HTTP Range",
                "sha512_zip_externo_conferido":False},True


def run_uf(uf,out):
    import asn1tools
    out=Path(out)
    out.parent.mkdir(parents=True,exist_ok=True)
    report={"projeto":"FATOVIA AUDITA","uf":uf,"turno":2,"ano":2026,
        "data_utc":datetime.now(timezone.utc).isoformat(),
        "status":"INCONCLUSIVO","fontes":{},"cobertura":{},"verificacoes":{},
        "ocorrencias":{},"ocorrencias_amostra":{},"resultado_por_secao":{},
        "assinatura_criptografica_validada":False,
        "limitacoes":[
            "Somente dados totalizados publicados pelo TSE.",
            "Conferir SHA512 com VSC NÃO verifica criptograficamente a assinatura.",
            "Rastreabilidade dos dados internos não prova intenção do eleitor.",
            "Log com contingência pode exigir prova documental complementar.",
        ]}
    try:
        urls=published_urls(uf)
        report["fontes"]["catalogos"]=DATASETS
        report["fontes"]["origens"]=urls
        with TemporaryDirectory(prefix=f"fatovia-{uf}-") as tmp:
            bu_path,bu_meta=engine.checked_reference(urls["bu"],"bu.zip",tmp)
            ceft_path,ceft_meta=engine.checked_reference(urls["ceft"],"ceft.zip",tmp)
            report["fontes"]["bu"]=bu_meta
            report["fontes"]["ceft"]=ceft_meta
            bu,att,lines=engine.bu_reference(bu_path)
            ceft=engine.ceft_reference(ceft_path)
            print(f"{uf}: BU={len(bu)}, CEFT={len(ceft)}, BU_rows={lines}",flush=True)
            raw,raw_meta,remote=check_brutal_zip(urls["bruto"],urls["bruto_bytes"],tmp)
            report["fontes"]["arquivo_bruto"]=raw_meta
            rdvc=asn1tools.compile_files(str(SPEC/"rdv.asn1"),codec="ber")
            sigc=asn1tools.compile_files(str(SPEC/"assinatura.asn1"),codec="ber")
            try:
                with zipfile.ZipFile(raw) as archive:
                    sections,inv=file_index_uf(archive,uf)
                    keys=set(bu)|set(ceft)|set(sections)
                    missing={
                        "bu_sem_ceft":len(set(bu)-set(ceft)),
                        "bu_sem_pacote_bruto":len(set(bu)-set(sections)),
                        "ceft_sem_bu":len(set(ceft)-set(bu)),
                        "pacote_bruto_sem_bu":len(set(sections)-set(bu)),
                    }
                    report["cobertura"]={
                        "secoes_bu":len(bu),"secoes_ceft":len(ceft),
                        "secoes_pacote_bruto":len(sections),
                        "secoes_distintas":len(keys),
                        "secoes_processadas":0,"secoes_alertadas":0,
                        "chaves_sem_correspondencia":missing,
                        "inventario":inv,
                    }
                    tests=Counter()
                    errors=Counter()
                    samples=defaultdict(list)
                    for n,key in enumerate(sorted(keys),1):
                        try:
                            rec=engine.audit_section(archive,key,sections.get(key,{}),
                                                     bu,att,ceft,rdvc,sigc)
                        except Exception as exc:
                            rec={"secao":list(key),
                                 "alertas":["EXCECAO_AUDITORIA_SECAO"],
                                 "erro":f"{type(exc).__name__}: {exc}"}
                        for label in rec.get("alertas",[]):
                            errors[label]+=1
                            if len(samples[label])<15:
                                samples[label].append(list(key))
                        rr=rec.get("resultados",{})
                        tests["sha512_arquivos_ok"]+=rr.get("hashes_sha512",{}).get(
                            "arquivos_presentes_conferidos",0)
                        for field,nam in (
                            ("rdv","contagens_confere_bu"),
                            ("rdv","identidade_secao_confere"),
                            ("log","eventos_igual_comparecimento"),
                            ("proveniencia","identidade_rdv_confere_ceft"),
                            ("proveniencia","carga_rdv_confere_ceft"),
                            ("proveniencia","urna_efetivada_no_log"),
                        ):
                            if rr.get(field,{}).get(nam) is True:
                                tests[f"{field}_{nam}_ok"]+=1
                        if rr.get("log",{}).get("aplicavel") is False:
                            tests["logs_nao_aplicaveis"]+=1
                        if rr.get("proveniencia",{}).get("urna_prevista_diferente_da_efetivada") is True:
                            tests["urnas_trocadas"]+=1
                        if rec.get("alertas"):
                            report["resultado_por_secao"]["/".join(map(str,key))]=rec
                        report["cobertura"]["secoes_processadas"]=n
                        if n%2000==0:
                            print(f"{uf}: {n}/{len(keys)} processadas, "
                                  f"alertas={sum(errors.values())}",flush=True)
                    report["cobertura"]["secoes_alertadas"]=len(report["resultado_por_secao"])
                    report["ocorrencias"]=dict(errors)
                    report["ocorrencias_amostra"]=dict(samples)
                    report["verificacoes"]=dict(tests)
                    if (report["cobertura"]["secoes_processadas"]!=len(keys)
                            or any(missing.values())
                            or inv["secoes_com_tipos_incompletos"]
                            or inv["arquivos_duplicados"]):
                        report["status"]="INCONCLUSIVO"
                    elif errors:
                        report["status"]="ALERTAS_TECNICOS_REQUEREM_ANALISE"
                    else:
                        report["status"]="CONFERENCIA_INTERNA_CONSISTENTE_COM_RESSALVAS"
            finally:
                if remote:
                    report["fontes"]["arquivo_bruto"]["bytes_transferidos_por_range"]=raw.bytes_fetched
                    report["fontes"]["arquivo_bruto"]["requisicoes_range"]=raw.http_requests
                    raw.close()
    except Exception as exc:
        report["status"]="INCONCLUSIVO"
        report["erro"]=f"{type(exc).__name__}: {exc}"
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n",
                   encoding="utf-8")
    summary={k:report.get(k) for k in ("uf","status","cobertura","verificacoes","ocorrencias","erro")}
    print(json.dumps(summary,ensure_ascii=False,default=str),flush=True)
    return report["status"]!="INCONCLUSIVO"


def main():
    args=argparse.ArgumentParser()
    args.add_argument("--uf",required=True,choices=UFS)
    args.add_argument("--out",default=None)
    cli=args.parse_args()
    out=cli.out or f"work/brasil/{cli.uf}.json"
    if not run_uf(cli.uf,out):
        raise SystemExit(2)

if __name__=="__main__":
    main()
