import unittest,json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from fatovia.factory_orchestrator import cycle,correct,queue_fixture,risk_gate,safe_research_input,task_key
from fatovia.audiovisual_factory import GateError

ROOT=Path(__file__).resolve().parents[1]
F=ROOT/"data/audiovisual_factory/fixtures"
def fx():return json.loads((F/"obras_v1.json").read_text())
def script():return json.loads((F/"obras_script.json").read_text())

class SafeOrchestrationTest(unittest.TestCase):
    def test_discovery_only_never_carries_unaudited_claim(self):
        news={"signals":[{"id":"one","status":"discovery_only","url":"https://agenciabrasil.ebc.com.br/teste","topics":["saude"]}]}
        plan=safe_research_input(news,[])
        self.assertFalse(plan["publication_authorized"])
        self.assertEqual(plan["signals"][0]["claims"],[])
        self.assertEqual(plan["signals"][0]["status"],"research_required")
    def test_source_checked_story_eligible_for_lab_only(self):
        r=queue_fixture(fx(),script(),[])
        self.assertEqual(r["action"],"render_lab")
        self.assertFalse(r["publish_allowed"])
        self.assertEqual(r["voice"],"Santa-R-1.0")
    def test_duplicate_protection_in_lab(self):
        item=fx()
        self.assertEqual(queue_fixture(item,script(),[{"story_id":item["id"]}])["action"],"skip_duplicate")
    def test_key_content_addressing(self):
        a=fx();self.assertEqual(task_key(a["source_urls"],a["id"],"a"*64),task_key(a["source_urls"],a["id"],"a"*64))
        self.assertNotEqual(task_key(a["source_urls"],a["id"],"a"*64),task_key(a["source_urls"],a["id"],"b"*64))
    def test_audio_repair_is_bounded(self):
        action=correct(["incomplete_speech_alignment"],{})[0]
        self.assertTrue(action["retry"])
        self.assertEqual(action["action"],"rerun_independent_asr_once")
        self.assertFalse(correct(["incomplete_speech_alignment"],{"incomplete_speech_alignment":2})[0]["retry"])
    def test_unknown_issue_not_self_healed_or_ignored(self):
        r=correct(["unsupported_political_claim"],{})[0]
        self.assertFalse(r["retry"]);self.assertEqual(r["action"],"audit_block_and_investigate")
    def test_no_gates_ever_bypassed(self):
        for issue in ["missing_logo","unverified_claim","wrong_account","stale_source","missing_media"]:
            self.assertFalse(correct([issue],{})[0]["retry"])
    def test_existing_publisher_required(self):
        now=datetime(2026,11,26,14,0,tzinfo=ZoneInfo("America/Sao_Paulo"))
        p=risk_gate({"published":[],"publishing":None},{"id":"reel:new"},now)
        self.assertEqual(p["decision"],"downstream_existing_publisher_required")
        self.assertFalse(p["publish_allowed"])
    def test_no_reel_if_already_published(self):
        now=datetime(2026,11,26,14,0,tzinfo=ZoneInfo("America/Sao_Paulo"))
        state={"published":[{"id":"reel:old","format":"reel","published_at":"2026-11-26T11:00:00-03:00"}],"publishing":None}
        self.assertEqual(risk_gate(state,{"id":"reel:new"},now)["decision"],"daily_reel_cap")
    def test_reconciliation_transaction_blocks(self):
        now=datetime(2026,11,26,14,0,tzinfo=ZoneInfo("America/Sao_Paulo"))
        self.assertEqual(risk_gate({"published":[],"publishing":{"id":"x"}},{"id":"y"},now)["decision"],"active_transaction")
    def test_full_cycle_does_not_publish(self):
        a=fx()
        r=cycle({"signals":[]},[],[a],{a["id"]:script()},[{"id":"maria","reach":242,"shares":2,"saves":1,"source":"instagram_live"}])
        self.assertFalse(r["publish_allowed"])
        self.assertEqual(r["max_spend_brl"],0)
        self.assertEqual(r["publisher"],"existing_only")
        self.assertEqual(r["plans"][0]["action"],"render_lab")
        self.assertEqual(r["learning"]["status"],"hypothesis_only_insufficient_sample")
if __name__=="__main__":unittest.main()
