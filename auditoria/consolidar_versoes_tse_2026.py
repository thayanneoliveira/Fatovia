"""Consolida comparação de versões TSE das 28 UFs. Não infere motivo da mudança."""
import json
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
from .tse import UFS

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--in-dir",required=True)
    p.add_argument("--out-dir",required=True)
    a=p.parse_args()
    directory=Path(a.in_dir);dest=Path(a.out_dir);dest.mkdir(parents=True,exist_ok=True)
    rows=[]
    counts=Counter()
    for uf in UFS:
        file=directory/(uf+".json")
        if not file.exists():
            item={"uf":uf,"status":"NAO_EXECUTADO","resultados":{}}
        else:
            try:
                item=json.loads(file.read_text(encoding="utf-8"))
            except Exception as exc:
                item={"uf":uf,"status":"INCONCLUSIVO","erro":str(exc),"resultados":{}}
        out={"uf":uf}
        for kind in ("bu","ceft","bruto"):
            d=item.get("resultados",{}).get(kind,{})
            state=d.get("status","NAO_EXECUTADO")
            out[kind]=state
            out[kind+"_sha512_anterior"]=d.get("hash_anterior")
            out[kind+"_sha512_atual"]=d.get("hash_atual")
            out[kind+"_bytes_anteriores"]=d.get("bytes_anteriores")
            out[kind+"_bytes_atuais"]=d.get("bytes_atuais",d.get("head",{}).get("content_length"))
            out[kind+"_last_modified"]=d.get("head",{}).get("last_modified")
            out[kind+"_etag"]=d.get("head",{}).get("etag")
            counts[kind+":"+state]+=1
        rows.append(out)
    summary={"projeto":"FATOVIA AUDITA","data_utc":datetime.now(timezone.utc).isoformat(),
        "marco_historico":"28/10/2026 (FatoVia, não primeira versão do TSE)",
        "total_ufs":len(UFS),"contagens":dict(counts),"por_uf":rows,
        "limitacoes":[
            "Hash SHA512 comparado dos bytes para BU/CEFT; para pacotes brutos de grande porte, só metadados HEAD.",
            "Tamanho igual não significa conteúdo igual.",
            "Mesmo hash de BU não equivale a ausência de fraude; hash diferente não demonstra investigação.",
            "Motivos de republicação somente podem ser comprovados por documentação oficial e versões originais arquivadas.",
        ]}
    (dest/"comparacao-versoes-2026-2t.json").write_text(
        json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    lines=["# FATOVIA AUDITA | Comparação das versões dos arquivos TSE 2026",
        "","**Baseline:** capturas do FatoVia em 28/10/2026, e não necessariamente primeiro arquivo publicado pelo TSE.",
        "", "**Data da conferência:** "+summary["data_utc"]+".",
        "","| UF | BU (SHA512) | CEFT (SHA512) | Pacote bruto |",
        "|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['uf']} | {r['bu']} | {r['ceft']} | {r['bruto']} |")
    lines.extend(["", "## Contadores", ""])
    for key,val in sorted(counts.items()):
        lines.append(f"- {key}: {val}")
    lines.extend(["","## Interpretação", ""])
    for note in summary["limitacoes"]:
        lines.append("- "+note)
    lines.append("")
    (dest/"comparacao-versoes-2026-2t.md").write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({"contagens":dict(counts)},ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
