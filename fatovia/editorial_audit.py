"""Independent documentary review; never imports or invokes the Meta publisher."""
import copy
import hashlib
import json
import re
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from .engine import load, save, now_local, validate_candidate
from .evidence import sealed, fingerprint, verify_live
from .render import render
from .claim_matrix import build, digest

REPORT=Path("data/editorial_audit.json")
PAGE_ROOT="https://thayanneoliveira.github.io/Fatovia"
POLICY="documentary-template-v2-claims"
MAX_BYTES=8_000_000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def paths_for(item):
    ident=item["id"].replace(":","-")
    version=item["version"]
    if not re.fullmatch(r"camara-[0-9]+",ident) or not re.fullmatch(r"[0-9a-f]{14}",version):
        raise ValueError("invalid_path_identity")
    return [f"docs/media/{ident}/{version}/{i:02}.jpg" for i in range(1,8)]


def inspect_files(item):
    expected=paths_for(item)
    if item.get("cards")!=expected:
        raise ValueError("unexpected_card_paths")
    result=[]
    for path in expected:
        p=Path(path)
        if p.is_symlink() or not p.is_file() or p.stat().st_size>MAX_BYTES:
            raise ValueError("invalid_card_file")
        if not p.resolve().is_relative_to(Path("docs/media").resolve()):
            raise ValueError("card_outside_media")
        data=p.read_bytes()
        if not data.startswith(b"\xff\xd8\xff"):
            raise ValueError("not_jpeg")
        result.append(sha(data))
    return result


def review(item,now,source_check=verify_live):
    row={"id":item.get("id"),"version":item.get("version"),"decision":"rejected",
         "checked_at":now.isoformat(),"policy":POLICY,"issues":[]}
    issues=row["issues"]
    if item.get("status")!="ready" or validate_candidate(item) or not sealed(item,now):
        issues.append("document_or_seal_invalid")
        return row
    if not source_check(item):
        issues.append("source_unavailable_or_changed")
        return row
    try:
        matrix=build(item)
        actual=inspect_files(item)
        # Reconstruct the approved deterministic template from the verified document.
        # Never use arbitrary LLM narration in this approval path.
        with tempfile.TemporaryDirectory() as tmp:
            reconstructed=render(copy.deepcopy(item),tmp)
            expected=[sha(Path(p).read_bytes()) for p in reconstructed["cards"]]
        if item["caption"]!=reconstructed["caption"]:
            issues.append("caption_differs_from_template")
        if actual!=expected:
            issues.append("cards_differ_from_template")
        if not issues:
            row.update(decision="approved_documentary_only",content_sha256=fingerprint(item),card_sha256=actual,
                       claim_matrix=matrix,claim_matrix_sha256=digest(matrix))
    except Exception as exc:
        issues.append("render_or_file_check_"+type(exc).__name__)
    return row


def approved(item,now,report=None):
    try:
        report=load(REPORT) if report is None else report
        if not isinstance(report,dict) or report.get("policy")!=POLICY:
            return False
        rows=[r for r in report["reviews"] if r.get("id")==item.get("id") and r.get("version")==item.get("version")]
        if len(rows)!=1:
            return False
        row=rows[0]
        checked=datetime.fromisoformat(row["checked_at"])
        return (row["decision"]=="approved_documentary_only" and row.get("policy")==POLICY
                and not row.get("issues") and now-timedelta(hours=24)<=checked<=now
                and row["content_sha256"]==fingerprint(item) and row["card_sha256"]==inspect_files(item)
                and row["claim_matrix"]==build(item) and row["claim_matrix_sha256"]==digest(row["claim_matrix"]))
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        return False


def verify_hosted(item,now,session=None):
    # The bytes served publicly must match the audited local files.
    if not approved(item,now):
        return False
    import requests
    session=session or requests.Session()
    try:
        for path,expected in zip(paths_for(item),inspect_files(item)):
            url=PAGE_ROOT+"/"+quote(path.removeprefix("docs/"),safe="/")
            with session.get(url,stream=True,timeout=(5,15),allow_redirects=False) as response:
                if response.status_code!=200 or "image/jpeg" not in response.headers.get("content-type","").lower():
                    return False
                digest=hashlib.sha256()
                size=0
                for chunk in response.iter_content(65536):
                    size+=len(chunk)
                    if size>MAX_BYTES:
                        return False
                    digest.update(chunk)
                if digest.hexdigest()!=expected:
                    return False
        return True
    except Exception:
        return False


def main():
    now=now_local()
    state=load("data/state.json")
    rows=[review(item,now) for item in state.get("pending",[])[:8]]
    report={"policy":POLICY,"generated_at":now.isoformat(),"reviews":rows,
            "limitations":"Independent rule-based check of the official source, approved template and bytes; not general factual or semantic review."}
    save(REPORT,report)
    print(json.dumps({"reviewed":len(rows),"approved":sum(r["decision"]=="approved_documentary_only" for r in rows),
                      "rejected":sum(r["decision"]=="rejected" for r in rows),
                      "reasons":[{"id":r["id"],"issues":r["issues"]} for r in rows if r["issues"]]},ensure_ascii=False))


if __name__=="__main__":
    main()
