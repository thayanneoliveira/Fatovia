"""FATOVIA AUDITA | tabela urna ↔ cidade ↔ zona ↔ seção, 2º turno 2026.

Chave composta (UF, CD_MUNICIPIO, NR_ZONA, NR_SECAO); nunca equiparar
o identificador físico da urna ao código de seção. Origem: BWeb + CEFT TSE
com hashes SHA512 oficiais e referência de 28/10. Sem endereços pessoais.
"""
from __future__ import annotations
import argparse,csv,gzip,json,unicodedata
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
from tempfile import TemporaryDirectory
from .tse import UFS,csv_rows
from .ma_integral import checked_reference
from .proveniencia_ma import read_selected_rows
from .brasil_2026 import published_urls

HEADER=("uf","cod_municipio_tse","nome_municipio","zona","secao",
    "cod_local_votacao","urna_prevista","urna_efetivada","tipo_divergencia",
    "origem_voto","urna_substituida","aptos","comparecimento",
    "sem_biometria","votos_13","votos_22","brancos","nulos","votos_validos")
META=("nome_municipio","cod_local_votacao","aptos","comparecimento","sem_biometria")
NUMS={"13":"votos_13","22":"votos_22","95":"brancos","96":"nulos"}

def norm_name(value):
    return unicodedata.normalize("NFC",value.strip()).upper()

def read_bweb(path,uf):
    data={}
    names={}
    # Validação por linha e consistência de município. Zero não é dado ausente.
    for row in csv_rows(path):
        if row.get("NR_TURNO")!="2" or row.get("CD_CARGO_PERGUNTA")!="1":continue
        if row["SG_UF"]!=uf:raise ValueError("UF no arquivo BWeb diferente do esperado")
        for required in ("NM_MUNICIPIO","NR_LOCAL_VOTACAO","QT_ELEI_BIOM_SEM_HABILITACAO"):
            if required not in row:
                raise ValueError(f"Coluna BWeb ausente: {required}")
        key=tuple(int(row[k]) for k in ("CD_MUNICIPIO","NR_ZONA","NR_SECAO"))
        city=norm_name(row["NM_MUNICIPIO"])
        if not city:raise ValueError(f"Nome do município vazio: {key}")
        if key[0] in names and names[key[0]]!=city:
            raise ValueError(f"Código município {key[0]} com nomes conflitantes")
        names[key[0]]=city
        meta={"nome_municipio":city,"cod_local_votacao":row["NR_LOCAL_VOTACAO"],
            "aptos":int(row["QT_APTOS"]),"comparecimento":int(row["QT_COMPARECIMENTO"]),
            "sem_biometria":int(row["QT_ELEI_BIOM_SEM_HABILITACAO"])}
        if key not in data:
            data[key]={**meta,**{c:0 for c in NUMS.values()}}
        elif any(data[key][k]!=v for k,v in meta.items()):
            raise ValueError(f"Metadados alterados dentro da mesma seção {key}")
        v=str(int(row["NR_VOTAVEL"]))
        if v not in NUMS:raise ValueError(f"Votável inesperado: {v}")
        qty=int(row["QT_VOTOS"])
        if qty<0:raise ValueError(f"Voto negativo {key}")
        data[key][NUMS[v]]+=qty
    if not data:raise ValueError("Nenhuma seção no BWeb")
    for key,val in data.items():
        if sum(val[c] for c in NUMS.values())!=val["comparecimento"]:
            raise ValueError(f"Votos e comparecimento diferem em {key}")
        if not 0<=val["sem_biometria"]<=val["comparecimento"]<=val["aptos"]:
            raise ValueError(f"Contagens impossíveis {key}")
    return data,names

def read_ceft(path):
    data={}
    for row in read_selected_rows(path,"ceft_"):
        key=tuple(int(row[k]) for k in ("CD_MUNICIPIO","NR_ZONA","NR_SECAO"))
        if key in data:raise ValueError(f"Seção CEFT duplicada: {key}")
        data[key]={
            "urna_prevista":row.get("NR_URNA_ESPERADA",""),
            "urna_efetivada":row.get("NR_URNA_EFETIVADA",""),
            "tipo_divergencia":row.get("TP_DIVERGENCIA",""),
            "origem_voto":row.get("DS_ORIGEM_VOTO",""),
        }
    return data

def audit_uf(uf,outdir):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    report={"uf":uf,"ano":2026,"turno":2,"gerado_utc":datetime.now(timezone.utc).isoformat(),
        "status":"INCONCLUSIVO","fontes":{},"contagens":{},"alertas":[]}
    target=outdir/(uf+".csv.gz")
    try:
        ref=json.loads(Path("docs/auditoria/2026-2t-presidente.json").read_text(encoding="utf-8"))["arquivos_por_uf"][uf]
        urls=published_urls(uf)
        if urls["bu"]!=ref["url"]:
            raise ValueError(f"URL BU diferente do snapshot histórico de 28/10 para {uf}")
        with TemporaryDirectory(prefix=f"fatovia-geo-{uf}-") as temp:
            bu_path,bu_meta=checked_reference(urls["bu"],"bu.zip",temp)
            ceft_path,ceft_meta=checked_reference(urls["ceft"],"ceft.zip",temp)
            if bu_meta["sha512"]!=ref["sha512_calculado"]:
                raise ValueError("Hash BU mudou comparado ao snapshot preservado")
            bu,names=read_bweb(bu_path,uf)
            ceft=read_ceft(ceft_path)
            missing_bu=set(ceft)-set(bu)
            missing_ceft=set(bu)-set(ceft)
            duplicates_by_urn=defaultdict(list)
            changed=Counter()
            for key,data in ceft.items():
                urn=data["urna_efetivada"].strip()
                if urn:
                    duplicates_by_urn[urn].append(key)
                if data["urna_prevista"] and urn and data["urna_prevista"]!=urn:
                    changed["substituicoes"]+=1
            dup={urn:ks for urn,ks in duplicates_by_urn.items() if len(ks)>1}
            if missing_bu or missing_ceft:
                report["alertas"].append("CHAVES_BU_CEFT_DIVERGENTES")
            if dup:report["alertas"].append("IDENTIFICADORES_URNA_REUTILIZADOS")
            counts=Counter()
            cities=Counter()
            with gzip.open(target,"wt",newline="",encoding="utf-8") as handle:
                writer=csv.DictWriter(handle,fieldnames=HEADER)
                writer.writeheader()
                for key,x in sorted(bu.items()):
                    c=ceft.get(key,{})
                    switched=(c.get("urna_prevista") and c.get("urna_efetivada") and
                              c["urna_prevista"]!=c["urna_efetivada"])
                    row={"uf":uf,"cod_municipio_tse":key[0],"nome_municipio":x["nome_municipio"],
                         "zona":key[1],"secao":key[2],
                         "urna_prevista":c.get("urna_prevista",""),
                         "urna_efetivada":c.get("urna_efetivada",""),
                         "tipo_divergencia":c.get("tipo_divergencia",""),
                         "origem_voto":c.get("origem_voto",""),
                         "urna_substituida":int(bool(switched)),
                         "votos_validos":x["votos_13"]+x["votos_22"],
                         **{k:x[k] for k in ("cod_local_votacao","aptos","comparecimento","sem_biometria",
                                          "votos_13","votos_22","brancos","nulos")}}
                    writer.writerow(row)
                    cities[x["nome_municipio"]]+=1
                    for k in ("aptos","comparecimento","sem_biometria","votos_13","votos_22","brancos","nulos"):
                        counts[k]+=x[k]
            report["contagens"]={
                "secoes_bu":len(bu),"secoes_ceft":len(ceft),
                "municipios_distintos":len(names),
                "nomes_distintos":len(cities),
                "secoes_ceft_sem_bu":len(missing_bu),
                "secoes_bu_sem_ceft":len(missing_ceft),
                "amostra_bu_sem_ceft":[list(x) for x in sorted(missing_ceft)[:10]],
                "amostra_ceft_sem_bu":[list(x) for x in sorted(missing_bu)[:10]],
                "urnas_identificador_duplicado":len(dup),
                "amostra_urna_duplicada":[{"urna":u,"secoes":[list(x) for x in v[:5]]}
                                          for u,v in list(dup.items())[:10]],
                "urnas_prevista_diferente_efetivada":changed["substituicoes"],
                "totais":dict(counts),
                "amostra_municipios":dict(sorted(cities.items())[:8]),
            }
            if len(bu)!=ref["secoes"]:raise ValueError("Total de seções não confere baseline")
            report["fontes"]={"BU":{"url":urls["bu"],"sha512":bu_meta["sha512"],"bytes":bu_meta["bytes"]},
                              "CEFT":{"url":urls["ceft"],"sha512":ceft_meta["sha512"],"bytes":ceft_meta["bytes"]}}
            report["status"]="OK" if not missing_bu and not missing_ceft else "ALERTAS_DE_COBERTURA"
    except Exception as exc:
        report["status"]="INCONCLUSIVO"
        report["erro"]=f"{type(exc).__name__}: {exc}"
        target.unlink(missing_ok=True)
    (outdir/(uf+".json")).write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"uf":uf,"status":report["status"],"contagens":report["contagens"],
        "erro":report.get("erro")},ensure_ascii=False),flush=True)
    return report["status"] in ("OK","ALERTAS_DE_COBERTURA")

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--uf",required=True,choices=UFS)
    a.add_argument("--out",default="work/geografia")
    s=a.parse_args()
    if not audit_uf(s.uf,s.out):raise SystemExit(2)

if __name__=="__main__":
    main()
