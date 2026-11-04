#!/usr/bin/env python3
"""Verificação pontual: hashes históricos de 29/10 versus referências atuais do TSE.

Não confundir: igualdade da referência publicada NÃO certifica imutabilidade do
arquivo remoto, autenticidade histórica ou ausência de novos recursos no catálogo.
Para correspondências/BU, existe também reaquisição e SHA de ZIP na auditoria v2.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime as dt
import io
import json
from pathlib import Path
import re
import time
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "auditoria-v2" / "monitoramento-artefatos"
OUT.mkdir(parents=True, exist_ok=True)
CROSS = ROOT / "auditoria-nacional-resultados" / "RESULTADO_NACIONAL_CRUZAMENTO.json"
GEDAI = ROOT / "auditoria-nacional-resultados" / "RESULTADO_NACIONAL_GEDAI.json"
HEX = re.compile(r"\b[a-fA-F0-9]{128}\b")
HEAD = {"User-Agent": "FatoVia-auditoria-comparativa/2026"}
CKAN = "https://dadosabertos.tse.jus.br/api/3/action/package_show?id="
DATASETS = {
    "GEDAI-2T": "resultados-2026-logs-do-sistema-de-preparacao-das-urnas-eletronicas-gedai-2-turno",
    "CORRESPONDENCIAS-2T": "resultados-2026-correspondencias-esperadas-e-efetivadas-2-turno",
    "BOLETIM": "resultados-2026-boletim-de-urna",
    "RESULTADOS-2026": "resultados-2026",
}

def get(url, limit=15*1024*1024):
    err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEAD)
            with urllib.request.urlopen(req, timeout=90) as response:
                content = response.read(limit + 1)
                if len(content) > limit:
                    raise RuntimeError("tamanho máximo excedido")
                return content, dict(response.headers)
        except Exception as ex:
            err = ex
            time.sleep(attempt+1)
    raise RuntimeError(f"{url}: {err}")

def parse_hash(raw):
    if zipfile.is_zipfile(io.BytesIO(raw)):
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names = [x for x in z.namelist() if not x.endswith("/")]
            if len(names) != 1:
                raise RuntimeError("hash de referência ZIP ambíguo")
            raw = z.read(names[0])
    hashes = {x.lower() for x in HEX.findall(raw.decode("utf-8-sig", errors="replace"))}
    if len(hashes) != 1:
        raise RuntimeError(f"referência contém {len(hashes)} hashes distintos")
    return next(iter(hashes))

def jobs():
    cross = json.loads(CROSS.read_text(encoding="utf-8"))
    gedai = json.loads(GEDAI.read_text(encoding="utf-8"))
    base = []
    for uf, state in cross["states"].items():
        for kind, source in state["sources"].items():
            base.append({
                "grupo": "correspondencias_e_BU", "uf": uf, "tipo": kind,
                "url": source["url"], "base_sha512": source.get("sha512_local"),
                "base_status": source.get("sha512_status"),
                "base_run_utc": cross.get("run_utc"),
            })
    for uf, state in gedai["ufs"].items():
        for kind, source in state["days"].items():
            base.append({
                "grupo": "GEDAI", "uf": uf, "tipo": kind,
                "url": source["url"], "base_sha512": source.get("sha512_local"),
                "base_status": source.get("hash_status"),
                "base_run_utc": gedai.get("run_at_utc"),
            })
    return base

def compare(entry):
    entry = dict(entry)
    try:
        if entry["base_status"] != "MATCH" or not entry["base_sha512"]:
            entry["status"] = "BASELINE_NAO_VERIFICADO"
            return entry
        raw, headers = get(entry["url"] + ".sha512")
        current = parse_hash(raw)
        entry.update({
            "status": "REFERENCIA_IGUAL" if current == entry["base_sha512"] else "REFERENCIA_ALTERADA",
            "current_reference_sha512": current,
            "reference_HTTP_last_modified": headers.get("Last-Modified"),
            "reference_HTTP_etag": headers.get("ETag"),
        })
    except Exception as exc:
        entry.update({"status": "INACESSIVEL_OU_ERRO", "erro": str(exc)})
    return entry

def catalog(name, slug, since):
    try:
        raw, headers = get(CKAN + slug, limit=20*1024*1024)
        answer = json.loads(raw)
        if not answer.get("success"):
            raise RuntimeError("CKAN respondeu sem sucesso")
        pkg = answer["result"]
        resources = pkg.get("resources", [])
        result = {
            "dataset": name, "dataset_slug": slug, "status": "CONSULTADO",
            "created": pkg.get("metadata_created"),
            "modified": pkg.get("metadata_modified"),
            "quantidade_recursos_atuais": len(resources),
            "resources_posteriores_a_base": [],
            "resources_sem_data": 0,
            "aviso": "Ausência de catálogo histórico impede afirmar que recursos foram adicionados depois da base apenas pelo estado atual.",
        }
        for r in resources:
            stamp = r.get("created") or r.get("last_modified")
            if not stamp:
                result["resources_sem_data"] += 1
            elif stamp[:10] > since[:10]:
                result["resources_posteriores_a_base"].append({
                    "name": r.get("name"), "id": r.get("id"),
                    "created": r.get("created"), "last_modified": r.get("last_modified"),
                    "url": r.get("url")
                })
        return result
    except Exception as exc:
        return {"dataset": name, "status": "INACESSIVEL_OU_ERRO", "erro": str(exc)}

def main():
    files = jobs()
    seen = set()
    for e in files:
        key = (e["grupo"],e["uf"],e["tipo"])
        if key in seen:
            raise RuntimeError(f"duplicado no baseline: {key}")
        seen.add(key)
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(compare, f) for f in files]
        rows = [f.result() for f in as_completed(futures)]
    rows.sort(key=lambda e: (e["grupo"],e["uf"],e["tipo"]))
    base_time = min(x["base_run_utc"] for x in rows if x.get("base_run_utc"))
    with ThreadPoolExecutor(max_workers=3) as pool:
        cats = list(pool.map(lambda kv: catalog(kv[0], kv[1], base_time),
                             DATASETS.items()))
    counters = {}
    for group in sorted({r["grupo"] for r in rows}):
        sub = [r for r in rows if r["grupo"] == group]
        counters[group] = {
            "total": len(sub),
            "referencia_igual": sum(r["status"] == "REFERENCIA_IGUAL" for r in sub),
            "referencia_alterada": sum(r["status"] == "REFERENCIA_ALTERADA" for r in sub),
            "nao_verificados": sum(r["status"] not in ("REFERENCIA_IGUAL","REFERENCIA_ALTERADA") for r in sub),
        }
    report = {
        "consulta_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "baseline_utc": base_time,
        "resumo": counters,
        "alterados": [r for r in rows if r["status"] == "REFERENCIA_ALTERADA"],
        "erros": [r for r in rows if r["status"] in ("BASELINE_NAO_VERIFICADO", "INACESSIVEL_OU_ERRO")],
        "catalogos": cats,
        "limites": [
            "Comparação dos SHA-512 das referências disponibilizadas pelo TSE com os registrados na coleta inicial.",
            "A verificação pontual NÃO baixa novamente o conteúdo ZIP. Para 112 arquivos, a auditoria v2 já baixou e validou os ZIPs nesta data.",
            "Para os 56 ZIPs GEDAI, comparação nesta execução é somente entre SHA-512 da coleta inicial e referência atualmente publicada.",
            "Não há snapshot anterior de recursos do CKAN; datas de catálogo posteriores à base não comprovam adição de recurso.",
            "Metadados HTTP Last-Modified/ETag podem referir-se a cache ou republicação, não necessariamente mudança de conteúdo."
        ]
    }
    (OUT/"comparacao_sha_referencias_tse_2026.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT/"inventario_168_arquivos.csv").write_text("grupo;uf;tipo;status;sha512_inicial;sha512_referencia_atual;url\n" +
        "\n".join(";".join([r["grupo"],r["uf"],r["tipo"],r["status"],
                       r.get("base_sha512") or "", r.get("current_reference_sha512") or "",r["url"]])
        for r in rows)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in ("catalogos","alterados","erros")},ensure_ascii=False,indent=2))
    print("CATALOGOS",json.dumps(cats,ensure_ascii=False)[:15000])
    if report["alterados"]: print("REFERENCIAS ALTERADAS",json.dumps(report["alterados"],ensure_ascii=False))
    if report["erros"]: print("ERROS",json.dumps(report["erros"],ensure_ascii=False)[:6000])
    # 0: todas 168 referencias iguais; 2: pelo menos uma mudou; 3: falha de cobertura.
    raise SystemExit(3 if report["erros"] else 2 if report["alterados"] else 0)

if __name__ == "__main__":
    main()
