"""Diagnóstico PASSIVO de 3 conjuntos publicados pelo TSE, segundo turno 2026.

Somente GET dos URLs publicados oficialmente, sem descoberta de rotas,
acesso autenticado, exploração de vulnerabilidade ou processamento de dados pessoais.
"""
from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import tempfile
import zipfile

from .tse import download_zip, sha512_expected, csv_rows

BASE="https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/"
FILES={
    "esperada_24": BASE+"correspesp/CESP_2t_MA_241020261231.zip",
    "esperada_25": BASE+"correspesp/CESP_2t_MA_251020261345.zip",
    "efetivada_26": BASE+"correspefet/CEFT_2t_MA_261020261201.zip",
    "bu_26": BASE+"buweb/bweb_2t_MA_261020260742.zip",
}

def inspect(name, path):
    contents=[]
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            obj={"arquivo":info.filename,"bytes":info.file_size}
            if info.filename.lower().endswith(".csv"):
                with z.open(info) as raw:
                    with io.TextIOWrapper(raw,encoding="latin-1",newline="") as stream:
                        rdr=csv.reader(stream,delimiter=";")
                        head=next(rdr,None)
                        obj["colunas"]=head
                        obj["linhas"]=sum(1 for _ in rdr)
            contents.append(obj)
    return contents


def read_selected_rows(path, needle):
    with zipfile.ZipFile(path) as z:
        matched=[n for n in z.namelist() if needle in n.lower() and n.lower().endswith(".csv")]
        if len(matched)!=1:
            raise ValueError(f"Esperado CSV único {needle}, encontrados {len(matched)}")
        with z.open(matched[0]) as raw:
            with io.TextIOWrapper(raw, encoding="latin-1", newline="") as stream:
                return list(csv.DictReader(stream, delimiter=";"))

def section_key(row):
    try:
        return (int(row["CD_MUNICIPIO"]),int(row["NR_ZONA"]),int(row["NR_SECAO"]))
    except (KeyError,ValueError) as exc:
        raise ValueError(f"Identificador de seção inválido: {exc}")

def keyed(rows,label):
    result={}
    duplicates=[]
    for r in rows:
        key=section_key(r)
        if key in result:
            duplicates.append(key)
        result[key]=r
    return result,duplicates

def summarize_comparison(paths):
    older,dup24=keyed(read_selected_rows(paths["esperada_24"],"csec_"),"24")
    latest,dup25=keyed(read_selected_rows(paths["esperada_25"],"csec_"),"25")
    effective,dup26=keyed(read_selected_rows(paths["efetivada_26"],"ceft_"),"26")
    bu=set()
    for row in csv_rows(paths["bu_26"]):
        if row.get("NR_TURNO")!="2":
            continue
        if row.get("CD_CARGO_PERGUNTA")!="1" and row.get("DS_CARGO_PERGUNTA","").casefold()!="presidente":
            continue
        bu.add(section_key(row))
    keys=[set(older),set(latest),set(effective),bu]
    samples=lambda s:[list(k) for k in sorted(s)[:20]]
    differences={}
    for col in ("NR_URNA_ESPERADA","CD_CARGA_URNA_ESPERADA","CD_FLASHCARD_URNA_ESPERADA","ST_CORRESP_ALTERADA","NR_LOCAL_VOTACAO"):
        changed=[k for k in (keys[0]&keys[1]) if older[k].get(col)!=latest[k].get(col)]
        differences[col]={"quantidade":len(changed),"amostra_secoes":samples(changed)}
    changed_urn=[k for k,r in effective.items()
                 if r.get("NR_URNA_ESPERADA") and r.get("NR_URNA_EFETIVADA")
                 and r["NR_URNA_ESPERADA"]!=r["NR_URNA_EFETIVADA"]]
    nonmatching_expected=[k for k,r in effective.items() if k in latest and
                          r.get("NR_URNA_ESPERADA","")!=latest[k].get("NR_URNA_ESPERADA","")]
    changed_without_code=[k for k in changed_urn if not effective[k].get("TP_DIVERGENCIA","").strip()]
    coded_without_number_change=[k for k,r in effective.items() if r.get("TP_DIVERGENCIA","").strip() and k not in changed_urn]
    # Campos administrativos públicos, sem dados de pessoas.
    detail_columns=("NR_URNA_ESPERADA","NR_URNA_EFETIVADA",
                    "CD_CARGA_URNA_ESPERADA","CD_CARGA_URNA_EFETIVADA",
                    "CD_FLASHCARD_URNA_ESPERADA","CD_FLASHCARD_URNA_EFETIVADA",
                    "CD_ORIGEM_VOTO","DS_ORIGEM_VOTO","TP_DIVERGENCIA")
    details_without_code=[
        {"secao":list(k), "campos":{p:effective[k].get(p,"") for p in detail_columns}}
        for k in sorted(changed_without_code)]
    classifications=Counter(r.get("TP_DIVERGENCIA","") or "(vazio)" for r in effective.values())
    origins=Counter(r.get("DS_ORIGEM_VOTO","") or "(vazio)" for r in effective.values())
    coverage={
        "esperada_24":len(older),"esperada_25":len(latest),
        "efetivada_26":len(effective),"bu_presidente":len(bu),
        "efetivada_sem_bu":{"quantidade":len(keys[2]-keys[3]),"amostra_secoes":samples(keys[2]-keys[3])},
        "bu_sem_efetivada":{"quantidade":len(keys[3]-keys[2]),"amostra_secoes":samples(keys[3]-keys[2])},
        "esperada_25_sem_efetivada":{"quantidade":len(keys[1]-keys[2]),"amostra_secoes":samples(keys[1]-keys[2])},
        "efetivada_sem_esperada_25":{"quantidade":len(keys[2]-keys[1]),"amostra_secoes":samples(keys[2]-keys[1])},
        "duplicadas":{"24":len(dup24),"25":len(dup25),"26":len(dup26)},
    }
    return {
        "cobertura":coverage,
        "alteracoes_pre_eleicao":differences,
        "urnas_esperada_versus_efetivada":{
            "numero_urna_diferente":len(changed_urn),
            "amostra_secoes":samples(changed_urn),
            "urna_diferente_sem_codigo_divergencia":{
                "quantidade":len(changed_without_code),
                "secoes":samples(changed_without_code),
                "campos_para_investigacao":details_without_code},
            "codigo_divergencia_sem_numero_diferente":{
                "quantidade":len(coded_without_number_change),
                "secoes":samples(coded_without_number_change)},
            "urna_esperada_publicada_25_nao_bate_com_campo_de_ceft":len(nonmatching_expected),
            "amostra_nao_coincidentes":samples(nonmatching_expected),
        },
        "codigos_tipo_divergencia_ceft":dict(classifications),
        "origem_votos_ceft":dict(origins),
        "alerta_metodologico":("Divergência de equipamento, código TP_DIVERGENCIA e alteração antes do pleito "
                               "não são fraude por si. Consultar os PDF leia-me e os logs da urna para qualificar."),
    }

def main():
    result={"fase":"diagnostico_estrutura","uf":"MA","turno":2,
            "gerado_utc":datetime.now(timezone.utc).isoformat(),
            "observacao":"Fonte publicada no TSE; não se busca acesso a sistemas internos.",
            "arquivos":{}, "status":"OK"}
    with tempfile.TemporaryDirectory() as tmp:
        local_paths={}
        for name,url in FILES.items():
            item={"url":url,"hash_url":url+".sha512"}
            try:
                path=Path(tmp)/(name+".zip")
                expected=sha512_expected(item["hash_url"])
                actual,size=download_zip(url,path)
                item.update({"hash_sha512_publicado":expected,
                             "hash_sha512_calculado":actual,
                             "hash_conferido":actual==expected,
                             "bytes_zip":size})
                if not item["hash_conferido"]:
                    raise ValueError("SHA512 difere do publicado")
                item["conteudo"]=inspect(name,path)
                local_paths[name]=path
            except Exception as exc:
                item["erro"]=str(exc)
                result["status"]="INCONCLUSIVO"
            result["arquivos"][name]=item
        if result["status"]=="OK":
            result["analise"]=summarize_comparison(local_paths)
    Path("work/proveniencia").mkdir(parents=True,exist_ok=True)
    out="work/proveniencia/ma_estrutura.json"
    Path(out).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"detalhes":[
        {"arquivo":k,"hash_ok":v.get("hash_conferido"),
         "estrutura":v.get("conteudo"),"erro":v.get("erro")}
        for k,v in result["arquivos"].items()],
        "analise":result.get("analise")},indent=2,ensure_ascii=False))
    if result["status"]!="OK":
        raise SystemExit(1)

if __name__=="__main__":
    main()
