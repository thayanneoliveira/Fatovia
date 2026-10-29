"""FATOVIA AUDITA | identificação biométrica por seção, 2º turno 2026.

Fonte: BWeb TSE, com checksum SHA512 oficial e baseline FatoVia em 28/10.
Cada seção é contada UMA vez; campos do BU repetem-se nas linhas de candidatos.
Não vincula identificação alternativa a voto individual e não infere fraude.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import csv
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

from .ma_integral import checked_reference
from .tse import UFS, csv_rows

BASELINE=Path("docs/auditoria/2026-2t-presidente.json")
FIELDS=("SG_UF","NR_TURNO","CD_CARGO_PERGUNTA","CD_MUNICIPIO","NR_ZONA",
        "NR_SECAO","NR_VOTAVEL","QT_VOTOS","QT_APTOS","QT_COMPARECIMENTO",
        "QT_ABSTENCOES","QT_ELEI_BIOM_SEM_HABILITACAO")
OUTFIELDS=("uf","municipio","zona","secao","aptos","comparecimento",
           "sem_biometria","votos_13","votos_22","brancos","nulos",
           "votos_validos","taxa_biometria_alternativa","participacao_13",
           "taxa_comparecimento","tipo_urna","encerramento")
VOTABLES={"13":"votos_13","22":"votos_22","95":"brancos","96":"nulos"}
SECTION_META=("aptos","comparecimento","sem_biometria","abstencoes","tipo_urna","encerramento")


def intfield(row,name):
    value=str(row.get(name,"")).strip()
    if not value.isascii() or not value.isdigit():
        raise ValueError(f"Campo numérico obrigatório inválido: {name}={value[:24]!r}")
    return int(value)


def extraction(uf,outdir):
    outdir=Path(outdir)
    outdir.mkdir(parents=True,exist_ok=True)
    report={
        "projeto":"FATOVIA AUDITA","uf":uf,"ano":2026,"turno":2,
        "gerado_utc":datetime.now(timezone.utc).isoformat(),
        "status":"INCONCLUSIVO",
        "definicao":(
            "QT_ELEI_BIOM_SEM_HABILITACAO: contagem de eleitores sem habilitação "
            "biométrica registrada na urna; não é sinônimo de fraude, "
            "voto irregular ou identificação individual de uma candidatura."
        ),
        "metodo":"Uma linha consolidada por seção/cargo, evitando somar metadados repetidos nas linhas de votáveis",
        "fontes":{},"cobertura":{},"totais":{},"limitacoes":[
            "A métrica de identificação é agregada por seção, não vinculada ao voto individual.",
            "Uma associação estatística agregada não estabelece causalidade ou irregularidade.",
            "BWeb do TSE, não um conjunto independente coletado de BUs impressos.",
            "O significado operacional preciso do campo exige consulta ao leia-me oficial e regulamentos.",
        ]}
    output=outdir/(uf+".csv.gz")
    report_path=outdir/(uf+".json")
    try:
        snapshot=json.loads(BASELINE.read_text(encoding="utf-8"))
        prior=snapshot["arquivos_por_uf"][uf]
        url=prior["url"]
        parsed=urlparse(url)
        if (parsed.scheme!="https" or parsed.hostname!="cdn.tse.jus.br"
                or not parsed.path.startswith("/estatistica/sead/eleicoes/eleicoes2026/buweb/")
                or f"bweb_2t_{uf}_" not in parsed.path):
            raise ValueError("Fonte não é arquivo BWeb oficial do 2º turno esperado")
        with TemporaryDirectory(prefix=f"fatovia-bio-{uf}-") as tmp:
            zip_path,metadata=checked_reference(url,"bweb.zip",tmp)
            if metadata["sha512"]!=prior["sha512_calculado"]:
                raise ValueError("ZIP BWeb difere da referência de 28/10; análise bloqueada")
            report["fontes"]={"url":url,"sha512":metadata["sha512"],
                              "hash_publicado_conferido":True,
                              "hash_referencia_28_10_conferido":True,
                              "bytes":metadata["bytes"]}
            sections={}
            seen_headers=False
            row_count=0
            for row in csv_rows(zip_path):
                if not seen_headers:
                    missing=set(FIELDS)-set(row.keys())
                    if missing:
                        raise ValueError(f"Colunas obrigatórias ausentes no BWeb: {sorted(missing)}")
                    seen_headers=True
                if row.get("NR_TURNO")!="2" or row.get("CD_CARGO_PERGUNTA")!="1":
                    continue
                if row["SG_UF"]!=uf:
                    raise ValueError("UF divergente dentro do BWeb")
                key=(intfield(row,"CD_MUNICIPIO"),intfield(row,"NR_ZONA"),
                     intfield(row,"NR_SECAO"))
                v=str(intfield(row,"NR_VOTAVEL"))
                votes=intfield(row,"QT_VOTOS")
                if v not in VOTABLES:
                    raise ValueError(f"Votável presidencial inesperado em {key}: {v}")
                meta={
                    "aptos":intfield(row,"QT_APTOS"),
                    "comparecimento":intfield(row,"QT_COMPARECIMENTO"),
                    "sem_biometria":intfield(row,"QT_ELEI_BIOM_SEM_HABILITACAO"),
                    "abstencoes":intfield(row,"QT_ABSTENCOES"),
                    "tipo_urna":row.get("CD_TIPO_URNA",""),
                    "encerramento":row.get("DT_ENCERRAMENTO",""),
                }
                if key not in sections:
                    sections[key]={**meta,"votos_13":0,"votos_22":0,
                                   "brancos":0,"nulos":0}
                else:
                    for field in SECTION_META:
                        if sections[key][field]!=meta[field]:
                            raise ValueError(f"Metadado {field} mudou entre linhas da seção {key}")
                sections[key][VOTABLES[v]]+=votes
                row_count+=1
            if not sections:
                raise ValueError("Nenhuma seção presidencial de 2º turno")
            sections_n=len(sections)
            if sections_n!=prior["secoes"]:
                raise ValueError(f"Cobertura {sections_n} não confere baseline {prior['secoes']}")
            totals=Counter()
            n_valid=0
            n_blank=0
            n_invalid=0
            samples_bad=[]
            with gzip.open(output,"wt",newline="",encoding="utf-8",compresslevel=6) as handle:
                writer=csv.DictWriter(handle,fieldnames=OUTFIELDS)
                writer.writeheader()
                for key,values in sorted(sections.items()):
                    vote_sum=sum(values[c] for c in VOTABLES.values())
                    turnout=values["comparecimento"]
                    aptos=values["aptos"]
                    nonbio=values["sem_biometria"]
                    valid=values["votos_13"]+values["votos_22"]
                    bad=[]
                    if vote_sum!=turnout:bad.append("VOTOS_DIFERENTE_COMPARECIMENTO")
                    if turnout>aptos:bad.append("COMPARECIMENTO_ACIMA_APTOS")
                    if nonbio>turnout:bad.append("SEM_BIOMETRIA_ACIMA_COMPARECIMENTO")
                    if aptos!=turnout+values["abstencoes"]:
                        bad.append("ABSTENCOES_INCONSISTENTES")
                    if bad:
                        n_invalid+=1
                        if len(samples_bad)<40:
                            samples_bad.append({"secao":list(key),"erros":bad})
                        continue
                    if turnout==0:
                        n_blank+=1
                    if valid:
                        n_valid+=1
                    writer.writerow({
                        "uf":uf,"municipio":key[0],"zona":key[1],"secao":key[2],
                        "aptos":aptos,"comparecimento":turnout,
                        "sem_biometria":nonbio,
                        "votos_13":values["votos_13"],"votos_22":values["votos_22"],
                        "brancos":values["brancos"],"nulos":values["nulos"],
                        "votos_validos":valid,
                        "taxa_biometria_alternativa":f"{nonbio/turnout:.12f}" if turnout else "",
                        "participacao_13":f"{values['votos_13']/valid:.12f}" if valid else "",
                        "taxa_comparecimento":f"{turnout/aptos:.12f}" if aptos else "",
                        "tipo_urna":values["tipo_urna"],
                        "encerramento":values["encerramento"],
                    })
                    totals["aptos"]+=aptos
                    totals["comparecimento"]+=turnout
                    totals["sem_biometria"]+=nonbio
                    for kind in VOTABLES.values():totals[kind]+=values[kind]
            report["cobertura"]={
                "secoes":sections_n,"linhas_bweb":row_count,
                "secoes_exportadas":sections_n-n_invalid,
                "secoes_com_votos_validos":n_valid,
                "secoes_sem_comparecimento":n_blank,
                "secoes_invalidas":n_invalid,
                "amostra_erros":samples_bad,
            }
            report["totais"]=dict(totals)
            report["totais"]["taxa_sem_biometria_comparecimento"]=(
                totals["sem_biometria"]/totals["comparecimento"]
                if totals["comparecimento"] else None)
            report["totais"]["votos_validos"]=totals["votos_13"]+totals["votos_22"]
            report["status"]="OK" if n_invalid==0 else "ALERTAS_DE_QUALIDADE"
            print(f"{uf}: {sections_n} seções, biometria_alternativa={totals['sem_biometria']}, "
                  f"comparecimento={totals['comparecimento']}, inválidas={n_invalid}",flush=True)
    except Exception as exc:
        report["status"]="INCONCLUSIVO"
        report["erro"]=f"{type(exc).__name__}: {exc}"
        if output.exists():output.unlink()
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"uf":uf,"status":report["status"],"cobertura":report["cobertura"],
                      "totais":report["totais"],"erro":report.get("erro")},ensure_ascii=False),flush=True)
    return report["status"]=="OK"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--uf",required=True,choices=UFS)
    p.add_argument("--out",default="work/biometria")
    args=p.parse_args()
    if not extraction(args.uf,args.out):
        raise SystemExit(2)

if __name__=="__main__":
    main()
