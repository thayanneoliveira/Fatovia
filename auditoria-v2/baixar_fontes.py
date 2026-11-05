#!/usr/bin/env python3
"""Aquisição reprodutível de arquivos públicos de correspondência e BU web do TSE."""
import argparse
import hashlib
import json
import pathlib
import sys
import time
import urllib.request
from importlib.machinery import SourceFileLoader
from pathlib import Path

audit = SourceFileLoader("audit", str(Path(__file__).with_name("reconciliar_secoes.py"))).load_module()
FOLDERS = {"24": "correspesp", "25": "correspesp", "efetivada": "correspefet", "bu": "buweb"}
BASE = "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/"

def download(url, dest, max_bytes=1024**3):
    if dest.exists() and dest.stat().st_size > 0:
        return "cached"
    tmp = Path(str(dest) + ".part")
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FatoVia-auditoria-v2/2026"})
            with urllib.request.urlopen(req, timeout=120) as res, tmp.open("wb") as f:
                received = 0
                for part in iter(lambda: res.read(1024*1024), b""):
                    received += len(part)
                    if received > max_bytes:
                        raise ValueError("limite de download por arquivo excedido")
                    f.write(part)
            tmp.replace(dest)
            return "downloaded"
        except Exception as e:
            if tmp.exists():
                tmp.unlink()
            if attempt == 2:
                raise RuntimeError(f"{url}: {e}") from e
            time.sleep(attempt + 1)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--ufs", nargs="+", choices=audit.UFS, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for uf in args.ufs:
        for kind, pattern in audit.PATTERNS.items():
            name = pattern.format(uf=uf)
            for suffix in ("", ".sha512"):
                target = args.out / (name + suffix)
                url = BASE + FOLDERS[kind] + "/" + name + suffix
                status = download(url, target)
                print(uf, kind, suffix or "zip", status, target.stat().st_size, flush=True)

if __name__ == "__main__":
    main()
