"""Lifecycle check for Instagram Login. Never persist or print token material."""
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PATH = Path("data/meta_token_lifecycle.json")
WINDOW = 15 * 86400
REPO = "thayanneoliveira/fatovia"


def stop(message):
    raise SystemExit(message)


def gh(*args):
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode:
        stop("GitHub API operation failed; inspect rotator permissions.")
    return result.stdout


def secret_updated_at(repo):
    try:
        value = json.loads(gh("api", f"repos/{repo}/actions/secrets/META_ACCESS_TOKEN"))["updated_at"]
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value
    except (ValueError, KeyError, TypeError, AttributeError):
        stop("Missing secret metadata; no renewal attempted.")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def meta_read(url, token=None):
    headers = {"Authorization": "Bearer " + token} if token else {}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.build_opener(NoRedirect).open(req, timeout=25) as response:
            result = json.load(response)
            if isinstance(result, dict) and not result.get("error"):
                return result
    except urllib.error.HTTPError as exc:
        print("Meta HTTP status:", exc.code)
    except Exception:
        print("Meta transport or response failure.")
    return None


def valid(token, ig):
    me = meta_read("https://graph.instagram.com/v25.0/me?fields=user_id,username", token)
    return bool(me and str(me.get("user_id")) == ig
                and str(me.get("username", "")).lower() == "fato.via")


def remaining_days(expires, now):
    return (expires - now) / 86400


def should_renew(expires, now):
    return 0 < expires - now <= WINDOW


def persist(metadata):
    PATH.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    for args in [
        ["git", "config", "user.name", "github-actions[bot]"],
        ["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"],
        ["git", "add", str(PATH)],
        ["git", "commit", "-m", "FatoVia: update token lifecycle metadata [skip ci]"],
        ["git", "fetch", "origin", "main"],
        ["git", "rebase", "origin/main"],
        ["git", "push", "origin", "HEAD:main"],
    ]:
        if subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            stop("Lifecycle metadata not confirmed in GitHub; inspect repository before retry.")


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if repo.lower() != REPO or os.environ.get("GITHUB_REF") != "refs/heads/main":
        stop("Unapproved repository or branch.")
    token = os.environ.get("META_ACCESS_TOKEN", "").strip()
    ig = os.environ.get("META_IG_USER_ID", "").strip()
    if not token or not re.fullmatch(r"[0-9]{5,30}", ig) or not os.environ.get("GH_TOKEN"):
        stop("Missing Meta or rotator configuration.")
    try:
        metadata = json.loads(PATH.read_text())
        expiry = metadata["token_expires_at"]
        if type(expiry) is not int:
            raise ValueError()
    except (OSError, ValueError, KeyError, TypeError):
        stop("Missing or invalid expiration metadata; inspect official debugger.")
    if not valid(token, ig):
        stop("Authentication failed; reauthorization or investigation required.")
    updated = secret_updated_at(repo)
    bound = metadata.get("secret_updated_at")
    if bound is not None and bound != updated:
        stop("Meta secret changed outside lifecycle process; verify expiration and rebind metadata.")
    now = int(time.time())
    print("META_TOKEN_REMAINING_DAYS:", round(remaining_days(expiry, now), 2))
    data_expiry = metadata.get("data_access_expires_at")
    if type(data_expiry) is int:
        print("DATA_ACCESS_LAST_VERIFIED_REMAINING_DAYS:", round(remaining_days(data_expiry, now), 2))
        if data_expiry - now <= WINDOW:
            print("::warning::Recheck data-access expiration in Meta debugger; independent of token renewal.")
    if expiry <= now:
        stop("Recorded token expiration elapsed; inspect official debugger before proceeding.")
    if bound is None:
        metadata["secret_updated_at"] = updated
        persist(metadata)
        print("INITIAL_METADATA_BOUND")
    if not should_renew(expiry, now):
        print("HEALTH_OK: outside 15-day renewal window; token unchanged.")
        return
    if expiry - now <= 5 * 86400:
        print("::warning::Meta token inside critical 5-day window.")
    gh("api", f"repos/{repo}/actions/secrets/public-key")
    start = int(time.time())
    query = urllib.parse.urlencode({"grant_type": "ig_refresh_token", "access_token": token})
    result = meta_read("https://graph.instagram.com/refresh_access_token?" + query) or {}
    new = result.get("access_token")
    lifetime = result.get("expires_in")
    if not isinstance(new, str) or not re.fullmatch(r"[A-Za-z0-9._~-]+", new) or type(lifetime) is not int or lifetime <= 86400:
        stop("Meta renewal not confirmed; current secret remains unchanged.")
    print("::add-mask::" + new, flush=True)
    if not valid(new, ig):
        stop("Returned token failed account validation; not stored.")
    saved = subprocess.run(["gh", "secret", "set", "META_ACCESS_TOKEN", "--repo", repo],
                           input=new, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if saved.returncode:
        stop("Meta renewal returned a token, but GitHub save failed; manual recovery required.")
    metadata.update(token_expires_at=start + lifetime,
                    source="meta_refresh_expires_in",
                    secret_updated_at=secret_updated_at(repo),
                    last_refresh_at=start)
    # Data-access expiration is not returned by refresh. Retain last verified date.
    persist(metadata)
    print("RENEWAL_OK: credential and lifecycle metadata stored.")
    print("NEW_TOKEN_EXPIRATION_UTC:", datetime.fromtimestamp(metadata["token_expires_at"], timezone.utc).isoformat())


if __name__ == "__main__":
    main()
