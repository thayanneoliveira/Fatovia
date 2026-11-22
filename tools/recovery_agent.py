"""FatoVia recovery agent: deterministic diagnostics, no automatic gate bypass or Meta POST."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def diagnose():
    policy = read("data/multiformat_experiment.json")
    closure = read("data/pilot_incident_closure_20261121.json")
    state = read("data/state.json")
    findings = []
    def issue(code, evidence, remedy, safe_auto=False):
        findings.append({"code": code, "evidence": evidence, "remedy": remedy,
                         "safe_auto": safe_auto, "status": "blocked"})
    recon = closure.get("reconciliation", {})
    if recon.get("status") != "verified_against_live_meta" or not recon.get("account_id_verified"):
        issue("PILOT_META_RECONCILIATION", recon,
              "Read-only compare live @fato.via media IDs, destination account and ledger; record verifiable evidence.")
    if not closure.get("production_transition_authorized") or not (policy.get("pilot_transition") or {}).get("authorized"):
        issue("PRODUCTION_TRANSITION", {"closure": closure.get("production_transition_authorized"),
              "policy": (policy.get("pilot_transition") or {}).get("authorized")},
              "Authorize only after reconciliation, preserved incident and independent tests.")
    if not policy.get("approved_items"):
        issue("APPROVED_QUEUE_EMPTY", {"approved_items": 0},
              "Verify exact hosted Reel, V5, Santa R 1.0, logo and sources; bind evidence to one queue item.")
    if state.get("publishing") is not None:
        issue("UNRESOLVED_CHECKPOINT", {"checkpoint": state["publishing"]},
              "Reconcile against Meta before any new POST.")
    return {"schema": 1, "mode": "read_only_diagnosis", "publish_attempted": False,
            "gates_modified": False, "additional_spend_brl": 0, "findings": findings}

if __name__ == "__main__":
    print(json.dumps(diagnose(), ensure_ascii=False, indent=2))
