"""Reprocessa somente 16 seções que falharam por rede/HTTP Range em 28/10.

Não repete a auditoria nacional, não imprime sequências de RDV, não classifica
uma falha de transporte como fraude. Cada exceção tem até 3 novas tentativas
em conexões HTTP independentes; resultados são evidência agregada.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import zipfile

from .brasil_2026 import published_urls,file_index_uf
from .ma_arqurna_range import RemoteZip
from .ma_amostra_profunda import SPEC
from .ma_integral import audit_section,bu_reference,ceft_reference,checked_reference

EXCECOES={
    "BA":[(35157,155,172),(35157,155,173),(38490,2,555)],
    "MG":[(48216,174,32),(48658,184,561),(48658,184,563),
          (48658,184,565),(49298,18,71),(49590,210,426),(49590,210,428)],
    "RJ":[(58971,87,94),(58971,87,95),(58971,87,96),
          (58971,87,103),(58971,133,29),(59250,90,367)],
}
MAX_ATTEMPTS=3

def targeted_read(url,uf,key,bu,attendance,ceft,rdvc,sigc):
    last=None
    for attempt in range(1,MAX_ATTEMPTS+1):
        try:
            with RemoteZip(url=url) as reader:
                with zipfile.ZipFile(reader) as archive:
                    sections,_=file_index_uf(archive,uf)
                    if key not in sections:
                        raise ValueError("Seção não aparece no inventário do ZIP")
                    record=audit_section(archive,key,sections[key],bu,attendance,ceft,rdvc,sigc)
            return {"tentativas":attempt,
                    "status":"VERIFICADA" if not record["alertas"] else "ALERTAS_TECNICOS",
                    "alertas":record["alertas"],
                    "rdv_confere_bu":record["resultados"].get("rdv",{}).get("contagens_confere_bu"),
                    "log_confere_comparecimento":record["resultados"].get("log",{}).get("eventos_igual_comparecimento"),
                    "hashes_conferidos":record["resultados"].get("hashes_sha512",{}).get("arquivos_presentes_conferidos"),
                    "urna_confere_ceft":record["resultados"].get("proveniencia",{}).get("identidade_rdv_confere_ceft"),
                    "carga_confere_ceft":record["resultados"].get("proveniencia",{}).get("carga_rdv_confere_ceft"),
                   }
        except (OSError,TimeoutError,ValueError,zipfile.BadZipFile) as exc:
            last=f"{type(exc).__name__}: {exc}"
            print(f"{uf} {key}: tentativa {attempt}/{MAX_ATTEMPTS} falhou: {last}",flush=True)
            if attempt<MAX_ATTEMPTS:
                time.sleep(attempt*2)
    return {"tentativas":MAX_ATTEMPTS,"status":"INCONCLUSIVO",
            "alertas":["ERRO_REDE_OU_LEITURA_RECURRENTE"],"erro":last}


def main():
    import asn1tools
    p=argparse.ArgumentParser()
    p.add_argument("--uf",required=True,choices=sorted(EXCECOES))
    p.add_argument("--out",required=True)
    args=p.parse_args()
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    report={"uf":args.uf,"base":"2026-10-28", "data_utc":datetime.now(timezone.utc).isoformat(),
            "selecionadas":len(EXCECOES[args.uf]),"metodo":"Três tentativas de leitura de cada seção em conexões independentes",
            "secoes":{},"status":"INCONCLUSIVO"}
    try:
        urls=published_urls(args.uf)
        report["fontes"]=urls
        with TemporaryDirectory(prefix=f"fatovia-excecoes-{args.uf}-") as tmp:
            bu_file,_=checked_reference(urls["bu"],"bu.zip",tmp)
            ceft_file,_=checked_reference(urls["ceft"],"ceft.zip",tmp)
            bu,turnout,_=bu_reference(bu_file)
            ceft=ceft_reference(ceft_file)
            rdvc=asn1tools.compile_files(str(SPEC/"rdv.asn1"),codec="ber")
            sigc=asn1tools.compile_files(str(SPEC/"assinatura.asn1"),codec="ber")
            for key in EXCECOES[args.uf]:
                result=targeted_read(urls["bruto"],args.uf,key,bu,turnout,ceft,rdvc,sigc)
                report["secoes"]["/".join(map(str,key))]=result
                print(json.dumps({"uf":args.uf,"secao":key,**result},ensure_ascii=False),flush=True)
        statuses=Counter(v["status"] for v in report["secoes"].values())
        report["contadores"]=dict(statuses)
        report["status"]="COMPLETO_COM_RESSALVAS" if statuses["INCONCLUSIVO"]==0 else "INCONCLUSIVO"
    except Exception as exc:
        report["erro_uf"]=f"{type(exc).__name__}: {exc}"
    out.write_text(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"uf":args.uf,"status":report["status"],"contadores":report.get("contadores"),"erro_uf":report.get("erro_uf")},ensure_ascii=False),flush=True)
    if report["status"]=="INCONCLUSIVO":
        raise SystemExit(2)

if __name__=="__main__":
    main()
