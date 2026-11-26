import copy
import json
import unittest
from pathlib import Path
from fatovia.audiovisual_factory import (
 GateError, check_story, plan, independent_gate, learning_signal,
 choose_validated_fixture, official_url, digest, LOGO
)
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"data/audiovisual_factory/fixtures"
def fixture():
    return json.loads((BASE/"obras_v1.json").read_text())
def script():
    return json.loads((BASE/"obras_script.json").read_text())
def timeline(rows):
    out=[];cur=0
    for i in range(0,len(rows),3):
        b=rows[i:i+3];start=cur;cur+=10
        out.append(dict(phrase_first=i+1,phrase_last=i+len(b),start=start,end=cur,
                        caption=" ".join(x["caption"] for x in b)))
    return dict(profile="Santa-R-1.0",phrases=len(rows),blocks=out,duration=cur)
class FactoryContractTest(unittest.TestCase):
    def test_source_and_script_check(self):
        d=check_story(fixture(),script())
        self.assertEqual(d["beats"],18)
        self.assertEqual(len(d["sources"]),4)
        self.assertEqual(d["status"],"structural_pass_fact_review_pending")
    def test_story_is_not_publish_eligible(self):
        obj=plan(fixture(),script(),timeline(script()))
        self.assertFalse(obj["publish_allowed"]);self.assertEqual(len(obj["scenes"]),18)
        self.assertEqual(obj["scenes"][-1]["scene"],"brand")
    def test_voice_profile_cannot_be_replaced(self):
        voice=timeline(script());voice["profile"]="another-voice"
        with self.assertRaises(GateError):plan(fixture(),script(),voice)
    def test_missing_scene_rejected(self):
        f=fixture();f["beats"].pop()
        with self.assertRaises(GateError):check_story(f,script())
    def test_unmapped_source_rejected(self):
        f=fixture();f["beats"][8]["claim_ids"]=["unproven"]
        with self.assertRaises(GateError):check_story(f,script())
    def test_official_statement_must_have_source(self):
        f=fixture();f["beats"][8]["claim_ids"]=[]
        with self.assertRaises(GateError):check_story(f,script())
    def test_untrusted_source_rejected(self):
        f=fixture();f["source_urls"]=["https://foo.example.org"]
        with self.assertRaises(GateError):check_story(f,script())
    def test_disclaimer_spoken_blocked(self):
        rows=script();rows[4]["caption"]="EXEMPLO FICTÍCIO"
        with self.assertRaises(GateError):check_story(fixture(),rows)
    def test_speculation_needs_specialist(self):
        rows=script();rows[3]["caption"]="Houve um desvio"
        with self.assertRaises(GateError):check_story(fixture(),rows)
    def test_missing_word_review_blocks(self):
        p=plan(fixture(),script(),timeline(script()))
        tech={"valid":True,"logo_sha256":LOGO,"fps":24,"dimensions":[1080,1920],"sha256":"x"*64}
        fact={"reviewed_by_independent_agent":True,"uncorroborated_claims":[]}
        visual={"reviewed_by_independent_agent":True,"artistic_equivalence":"equivalent"}
        asr={"independent_recognition":False,"word_level_alignment_validated":False}
        q=independent_gate(p,tech,fact,visual,asr)
        self.assertEqual(q["decision"],"rejected")
        self.assertIn("word_level_subtitles_unverified",q["findings"])
    def test_audit_never_releases_meta(self):
        p=plan(fixture(),script(),timeline(script()))
        tech={"valid":True,"logo_sha256":LOGO,"fps":24,"dimensions":[1080,1920],"sha256":"x"*64}
        fact={"reviewed_by_independent_agent":True,"uncorroborated_claims":[]}
        visual={"reviewed_by_independent_agent":True,"artistic_equivalence":"equivalent"}
        asr={"independent_recognition":True,"word_level_alignment_validated":True}
        q=independent_gate(p,tech,fact,visual,asr)
        self.assertEqual(q["decision"],"independent_review_passed_only")
        self.assertIs(q["publish_allowed"],False)
    def test_metrics_not_fabricated_or_promoted(self):
        m=learning_signal([{"id":"maria","reach":241,"views":282,"shares":2,"saves":1,"source":"user-provided"}])
        self.assertEqual(m["samples"],1)
        self.assertFalse(m["eligible_for_strategy_change"])
        self.assertAlmostEqual(m["observations"][0]["shares_per_reach"],2/241)
    def test_missing_metric_not_imputed(self):
        self.assertEqual(learning_signal([{"reach":241,"shares":2}])["samples"],0)
    def test_duplicate_candidate_excluded(self):
        story=fixture()
        self.assertIsNone(choose_validated_fixture([story],[{"id":story["id"]}]))
        self.assertEqual(choose_validated_fixture([story],[])["id"],story["id"])
    def test_no_embedded_meta_token(self):
        from fatovia import audiovisual_factory as f
        self.assertNotIn("META_ACCESS_TOKEN",Path(f.__file__).read_text())
if __name__=="__main__":unittest.main()
