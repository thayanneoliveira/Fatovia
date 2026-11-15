"""Publicador seguro para Instagram. Nunca publica sem ativação explícita.

Uso: python -m fatovia.publisher status|prepare|deliver|reconcile
A confirmação da transação Git ocorre NO WORKFLOW, antes do primeiro POST da Meta.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import requests
from .evidence import sealed, verify_live
from .editorial_audit import approved, verify_hosted
from .pilot import allowed as pilot_allowed, window_slot

from .engine import TZ, MIN_PUBLICATION_GAP_HOURS, daily_limit, load, now_local, preferred_hours, save, validate_candidate

STATE_PATH = Path("data/state.json")
PAGE_ROOT = "https://thayanneoliveira.github.io/Fatovia"
TARGET_USERNAME = "fato.via"
API_HOSTS = {"graph.instagram.com", "graph.facebook.com"}
SENSITIVE_SUBJECT = re.compile(
    r"\b(?:corrupção|corrupcao|fraude eleitoral|denúncia|denuncia|acusação|acusacao|"
    r"investigação criminal|investigacao criminal|crime eleitoral)\b", re.I
)


class PublicationError(Exception):
    """Falha segura: não se deve repetir um POST automaticamente."""
    def __init__(self, message, code="publication_guard"):
        super().__init__(message)
        self.code = code


def config():
    host = (os.getenv("META_API_HOST") or "graph.instagram.com").strip().lower()
    version = (os.getenv("META_GRAPH_VERSION") or "v25.0").strip()
    if host not in API_HOSTS or not re.fullmatch(r"v\d+\.\d+", version):
        raise PublicationError("Host ou versão da API Meta não permitidos")
    return {
        "enabled": os.getenv("IG_PUBLISH_ENABLED", "").lower() == "true",
        "token": os.getenv("META_ACCESS_TOKEN", "").strip(),
        "ig_id": os.getenv("META_IG_USER_ID", "").strip(),
        "base": f"https://{host}/{version}",
    }


def qualified(item, now):
    if item.get("status") != "ready" or validate_candidate(item) or not sealed(item, now):
        return False
    try:
        published_stage = datetime.fromisoformat(item["stage_date"]).date()
        if not (0 <= (now.date() - published_stage).days <= 14):
            return False
    except (KeyError, ValueError):
        return False
    caption = item.get("caption", "")
    if not (50 <= len(caption) <= 2200) or "ID editorial:" not in caption:
        return False
    if SENSITIVE_SUBJECT.search(item.get("summary", "") + " " + caption):
        return False
    try:
        return len(public_urls(item)) == 7
    except PublicationError:
        return False


def public_urls(item):
    cards = item.get("cards", [])
    if not isinstance(cards, list) or len(cards) != 7:
        raise PublicationError("O carrossel precisa conter 7 cards")
    result = []
    for card in cards:
        if not isinstance(card, str):
            raise PublicationError("Caminho de card inválido")
        if not re.fullmatch(r"docs/media/[A-Za-z0-9_./-]+\.jpg", card):
            raise PublicationError("Caminho de JPEG fora do diretório público")
        components = Path(card).parts
        if ".." in components or len(components) < 5:
            raise PublicationError("Caminho de JPEG não permitido")
        result.append(PAGE_ROOT + "/" + quote(card.removeprefix("docs/"), safe="/"))
    if len(set(result)) != len(result):
        raise PublicationError("Cards duplicados")
    return result


def marker(item):
    base=f'ID editorial: {item["id"]}/{item["version"]}'
    return base+"/didactic-v4" if item.get("template_revision")=="didactic-v4" else base


def choose_due(state, now, approval_check=None, pilot_window=False):
    if now.date().isoformat() in state.get("blackout_dates", []):
        return None
    if pilot_window:
        if window_slot(now) is None:
            return None
    else:
        if not (8 <= now.hour <= 22) or now.hour not in preferred_hours(state):
            return None
        if now.minute > 45:
            return None
    today = []
    for p in state.get("published", []):
        try:
            stamp = datetime.fromisoformat(p["published_at"].replace("Z", "+00:00")).astimezone(TZ)
            if stamp.date() == now.date():
                today.append(stamp)
        except (KeyError, ValueError):
            continue
    if len(today) >= min(4, daily_limit(state)):
        return None
    if any((window_slot(stamp) == window_slot(now)) if pilot_window else (stamp.hour == now.hour) for stamp in today):
        return None
    if today and now - max(today) < timedelta(hours=MIN_PUBLICATION_GAP_HOURS):
        return None
    already = {(p.get("id"), p.get("version")) for p in state.get("published", [])}
    candidates = [
        p for p in state.get("pending", [])
        if qualified(p, now) and (p.get("id"), p.get("version")) not in already
        and (approval_check is None or approval_check(p, now))
    ]
    request=state.get("replacement_request") or {}
    if request.get("status") in ("awaiting_deletion","deletion_verified"):
        candidates=[p for p in candidates if (p.get("id"),p.get("version"))!=(request.get("id"),request.get("version")) or (request.get("status")=="deletion_verified" and window_slot(now)==9)]
    candidates.sort(key=lambda x: (0 if request.get("status")=="deletion_verified" and (x.get("id"),x.get("version"))==(request.get("id"),request.get("version")) else 1, -x.get("editorial_score", 0), -x.get("explore_signal_count",0), -x.get("discovery_source_count",0), x["id"]))
    return candidates[0] if candidates else None


def prepare(state, now, cfg):
    if not cfg["enabled"]:
        return {"action": "disabled", "reason": "IG_PUBLISH_ENABLED não está true"}
    if not cfg["token"] or not cfg["ig_id"].isdigit():
        return {"action": "missing_credentials", "reason": "Configuração Meta incompleta"}
    if state.get("publishing"):
        return {"action": "reconcile", "reason": "Publicação anterior requer conciliação"}
    request=state.get("replacement_request") or {}
    replacement_key=(request.get("id"),request.get("version"))
    # Explicit owner-authorized one-time replacement; only after full Meta history confirms old media absent.
    if request.get("status")=="awaiting_deletion" and window_slot(now)==9:
        replacement=next((p for p in state.get("pending",[]) if (p["id"],p["version"])==replacement_key),None)
        if replacement and approved(replacement,now) and replacement.get("template_revision")=="didactic-v4":
            client=MetaClient(cfg)
            client.account()
            history=client.recent()
            old_marker=f'ID editorial: {request["id"]}/{request["version"]}'
            if not any(str(m.get("id"))==str(request["old_media_id"]) or old_marker in (m.get("caption") or "").splitlines() for m in history):
                old=[p for p in state.get("published",[]) if str(p.get("media_id"))==str(request["old_media_id"]) and (p.get("id"),p.get("version"))==replacement_key]
                if len(old)!=1:
                    raise PublicationError("Registro original de substituição divergente","replacement_record_invalid")
                state["published"]=[p for p in state["published"] if p is not old[0]]
                state.setdefault("withdrawn_publications",[]).append({**old[0],"withdrawn_verified_at":now.isoformat(),"reason":"owner_requested_replacement"})
                request["status"]="deletion_verified"
                save(STATE_PATH,state)
    item = choose_due(state, now, approval_check=lambda p,t: approved(p,t) and pilot_allowed(state,p,t), pilot_window=True)
    if not item:
        return {"action": "idle", "reason": "Nenhuma pauta verificada e elegível neste horário"}
    state["publishing"] = {
        "id": item["id"],
        "version": item["version"],
        "started_at": now.isoformat(),
        "status": "checkpointed",
    }
    save(STATE_PATH, state)
    return {"action": "prepared", "id": item["id"], "version": item["version"]}


def media_item(state):
    tx = state.get("publishing")
    if not tx:
        raise PublicationError("Nenhuma transação em aberto")
    matching = [x for x in state.get("pending", []) if
                x.get("id") == tx.get("id") and x.get("version") == tx.get("version")]
    if len(matching) != 1:
        raise PublicationError("Registro editorial ausente ou ambíguo")
    return matching[0]


class MetaClient:
    def __init__(self, cfg, session=None):
        self.cfg = cfg
        self.session = session or requests.Session()

    def request(self, method, endpoint, *, params=None, data=None):
        # Dados são enviados via Authorization, nunca no query string ou nos logs.
        response = self.session.request(
            method, f'{self.cfg["base"]}/{endpoint.lstrip("/")}',
            headers={"Authorization": f'Bearer {self.cfg["token"]}', "Accept": "application/json"},
            params=params,
            data=data,
            timeout=25, allow_redirects=False,
        )
        response.raise_for_status()
        if response.status_code != 200:
            raise PublicationError("Resposta HTTP inesperada da Meta", "meta_http_unexpected")
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("error"):
            raise PublicationError("Resposta inesperada da Meta")
        return payload

    def account(self):
        # Instagram Login returns an app-scoped id distinct from the professional user_id.
        # Never fall back to username alone or interchange these identifiers.
        instagram_login = self.cfg["base"].startswith("https://graph.instagram.com/")
        if instagram_login:
            profile = self.request("GET", "me", params={"fields": "user_id,username"})
            identity = profile.get("user_id")
        else:
            profile = self.request("GET", self.cfg["ig_id"], params={"fields": "id,username"})
            identity = profile.get("id")
        if str(identity) != self.cfg["ig_id"] or str(profile.get("username", "")).casefold() != TARGET_USERNAME:
            raise PublicationError("Identidade Meta incompatível com a conta autorizada", "meta_identity_mismatch")
        return profile

    def recent(self):
        result = self.request(
            "GET", f'{self.cfg["ig_id"]}/media',
            params={"fields": "id,caption,permalink", "limit": 100},
        )
        rows = result.get("data")
        if not isinstance(rows, list) or any(not isinstance(m, dict) for m in rows):
            raise PublicationError("Histórico Meta indisponível", "meta_history_invalid")
        # Fail closed if the available history cannot establish absence.
        if result.get("paging", {}).get("next"):
            raise PublicationError("Histórico Meta paginado, ausência não demonstrada", "meta_history_incomplete")
        return rows

    def existing(self, item):
        key = marker(item)
        matches = [m for m in self.recent() if key in (m.get("caption") or "").splitlines() and m.get("id")]
        if len(matches) > 1:
            raise PublicationError("Marcador editorial duplicado na Meta", "meta_duplicate_marker")
        return matches[0] if matches else None

    def create(self, data):
        payload = self.request("POST", f'{self.cfg["ig_id"]}/media', data=data)
        if not payload.get("id"):
            raise PublicationError("Meta não retornou ID do contêiner")
        return str(payload["id"])

    def ready(self, container, attempts=6, sleep_fn=time.sleep):
        for i in range(attempts):
            status = self.request("GET", container, params={"fields": "status_code"}).get("status_code")
            if status == "FINISHED":
                return
            if status in {"ERROR", "EXPIRED", "PUBLISHED"}:
                raise PublicationError("Contêiner Meta não está disponível para publicação")
            if status != "IN_PROGRESS":
                raise PublicationError("Estado do contêiner desconhecido")
            if i + 1 < attempts:
                sleep_fn(25)
        raise PublicationError("Contêiner não ficou pronto; requer conciliação")

    def publish(self, container):
        result = self.request("POST", f'{self.cfg["ig_id"]}/media_publish',
                              data={"creation_id": container})
        if not result.get("id"):
            raise PublicationError("Resposta de publicação sem media_id")
        return str(result["id"])

    def permalink(self, mid):
        result = self.request("GET", mid, params={"fields": "id,permalink"})
        return result.get("permalink") if str(result.get("id")) == str(mid) else None


def verify_media(urls, http=None):
    session = http or requests.Session()
    for url in urls:
        if not url.startswith(PAGE_ROOT + "/media/"):
            raise PublicationError("URL fora da hospedagem permitida")
        head = session.head(url, timeout=15, allow_redirects=False)
        if head.status_code != 200:
            raise PublicationError("Imagem pública indisponível")
        if "image/jpeg" not in head.headers.get("content-type", "").lower():
            raise PublicationError("Formato da imagem pública não é JPEG")
        size = int(head.headers.get("content-length", "0") or 0)
        if size > 8_000_000:
            raise PublicationError("JPEG acima do limite do Instagram")
        response = session.get(url, timeout=20, headers={"Range": "bytes=0-2"},
                               stream=True, allow_redirects=False)
        try:
            if response.status_code not in (200, 206):
                raise PublicationError("Não foi possível ler JPEG público")
            prefix = next(response.iter_content(3), b"")
            if not prefix.startswith(b"\xff\xd8\xff"):
                raise PublicationError("Conteúdo não parece um JPEG válido")
        finally:
            response.close()


def finalize(state, item, mid, permalink, now):
    tx = state.get("publishing")
    if not tx or tx.get("id") != item["id"] or tx.get("version") != item["version"]:
        raise PublicationError("Transação mudou antes de finalizar")
    if not any(p.get("media_id") == mid for p in state.get("published", [])):
        state.setdefault("published", []).append({
            "id": item["id"], "version": item["version"], "media_id": mid,
            "permalink": permalink or "",
            "published_at": now.isoformat(), "title": item.get("title", ""),
            "topics": item.get("topics", []),
            "summary_hash": item.get("summary_hash", ""),
            "summary": item.get("summary", ""), "evidence_sha256": item.get("evidence", {}).get("content_sha256", ""),
        })
    state["pending"] = [x for x in state.get("pending", [])
                        if not (x.get("id") == item["id"] and x.get("version") == item["version"])]
    state["publishing"] = None
    request=state.get("replacement_request") or {}
    if (item.get("id"),item.get("version"))==(request.get("id"),request.get("version")) and request.get("status")=="deletion_verified":
        request.update(status="replaced",new_media_id=mid)
    save(STATE_PATH, state)


def deliver(state, now, cfg, client=None, http=None, source_check=verify_live):
    if not cfg["enabled"] or not cfg["token"] or not cfg["ig_id"].isdigit():
        raise PublicationError("Envio desabilitado ou sem credenciais")
    item = media_item(state)
    tx = state["publishing"]
    if tx["status"] != "checkpointed":
        raise PublicationError("Transação não permite novo POST; apenas conciliação")
    if now.date().isoformat() in state.get("blackout_dates", []):
        raise PublicationError("Bloqueio editorial da data")
    if not qualified(item, now):
        raise PublicationError("O conteúdo deixou de atender à verificação editorial")
    client = client or MetaClient(cfg)
    client.account()
    request=state.get("replacement_request") or {}
    if (item.get("id"),item.get("version"))==(request.get("id"),request.get("version")):
        if request.get("status")!="deletion_verified":
            raise PublicationError("Exclusão não verificada","replacement_not_verified")
        old_marker=f'ID editorial: {request["id"]}/{request["version"]}'
        if any(str(m.get("id"))==str(request["old_media_id"]) or old_marker in (m.get("caption") or "").splitlines() for m in client.recent()):
            raise PublicationError("Publicação antiga ainda visível","replacement_old_visible")
    found = client.existing(item)
    if found:
        finalize(state, item, str(found["id"]), found.get("permalink"), now)
        return {"action": "recovered", "media_id": str(found["id"])}
    if not pilot_allowed(state,item,now):
        raise PublicationError("Limite, prazo ou conteúdo do piloto fora da autorização")
    if not approved(item, now) or not verify_hosted(item, now):
        raise PublicationError("Parecer independente ausente, vencido ou bytes publicados divergentes")
    if not source_check(item):
        raise PublicationError("Fonte oficial mudou ou não respondeu; envio bloqueado")
    urls = public_urls(item)
    verify_media(urls, http=http)
    tx["status"] = "uncertain"  # Persistir antes do primeiro POST, sem retry cego.
    save(STATE_PATH, state)
    try:
        children = [client.create({"image_url": url, "is_carousel_item": "true"}) for url in urls]
        parent = client.create({
            "media_type": "CAROUSEL", "children": ",".join(children),
            "caption": item["caption"],
        })
        client.ready(parent)
        mid = client.publish(parent)
        try:
            permalink = client.permalink(mid)
        except requests.RequestException:
            permalink = None
        finalize(state, item, mid, permalink, now)
        return {"action": "published", "media_id": mid, "permalink": permalink}
    except Exception:
        # A API pode ter recebido o pedido mesmo sem resposta. Não publicar de novo.
        save(STATE_PATH, state)
        raise


def reconcile(state, now, cfg, client=None):
    if not cfg["enabled"] or not cfg["token"] or not cfg["ig_id"].isdigit():
        return {"action": "blocked", "reason": "Credenciais ausentes para conciliação"}
    item = media_item(state)
    client = client or MetaClient(cfg)
    client.account()
    found = client.existing(item)
    if found:
        finalize(state, item, str(found["id"]), found.get("permalink"), now)
        return {"action": "recovered", "media_id": str(found["id"])}
    state["publishing"]["status"] = "uncertain"
    save(STATE_PATH, state)
    return {"action": "needs_attention", "reason": "Sem confirmação da Meta. Nenhuma repetição automática."}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"status", "prepare", "deliver", "reconcile", "probe"}:
        raise SystemExit("Uso: python -m fatovia.publisher status|prepare|deliver|reconcile|probe")
    cmd = sys.argv[1]
    state = load(STATE_PATH)
    cfg = config()
    now = now_local()
    try:
        if cmd == "status":
            result = {
                "action": "status", "enabled": cfg["enabled"],
                "credentials_present": bool(cfg["token"] and cfg["ig_id"]),
                "pending": len(state.get("pending", [])),
                "transaction_open": bool(state.get("publishing")),
                "allowed_hours": preferred_hours(state),
                "limit": daily_limit(state),
                "pilot_recovery_windows_brt": ["09:00–11:00 (exclusive)", "17:00–19:00 (exclusive)"],
            }
        elif cmd == "probe":
            verify_media([PAGE_ROOT + "/media/healthcheck.jpg"])
            result = {"action": "hosting_verified", "status": "JPEG_PUBLIC_OK"}
        elif cmd == "prepare":
            result = prepare(state, now, cfg)
        elif cmd == "deliver":
            result = deliver(state, now, cfg)
        else:
            result = reconcile(state, now, cfg)
        print(json.dumps(result, ensure_ascii=False))
    except (PublicationError, requests.RequestException) as exc:
        result = {"action": "blocked", "reason": type(exc).__name__}
        if isinstance(exc, PublicationError):
            result["code"] = exc.code
        if isinstance(exc, requests.HTTPError) and exc.response is not None:
            result["http_status"] = exc.response.status_code
            try:
                api_error = exc.response.json().get("error", {})
                for field in ("code", "error_subcode"):
                    if type(api_error.get(field)) is int:
                        result["meta_"+field] = api_error[field]
            except (ValueError, TypeError, AttributeError):
                pass
        print(json.dumps(result, ensure_ascii=False))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
