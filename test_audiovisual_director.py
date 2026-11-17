import copy,unittest
from audiovisual_director import create_plan,choose

def fixture(texts):
    rows=[{"caption":t} for t in texts]
    manifest={"phrases":len(rows),"duration":len(rows)*2.,"sha256_mp3":"synthetic","blocks":[{"phrase_first":1,"phrase_last":len(rows),"spoken":" ".join(texts),"start":0.,"end":len(rows)*2.}]}
    audit={"phrase_count":len(rows),"audio_sha256":"synthetic","duration":len(rows)*2.,"status":"needs_review","candidate_cues":[{"phrase":i+1,"caption":t,"start":i*2.+.1,"end":i*2.+1.9} for i,t in enumerate(texts)]}
    return rows,manifest,audit
class DirectorTests(unittest.TestCase):
    def test_complete(self):
        p=create_plan(*fixture(["Uma casa.","Uma creche.","Consultar contrato."]))
        self.assertEqual(p["scene_count"],3);self.assertFalse(p["publish_allowed"]);self.assertEqual(p["scenes"][0]["start"],0);self.assertEqual(p["scenes"][-1]["end"],6)
    def test_incomplete_block(self):
        r,m,a=fixture(["Uma casa.","Uma creche."]);a["candidate_cues"].pop()
        p=create_plan(r,m,a);self.assertEqual(p["scene_count"],1);self.assertEqual(p["scenes"][0]["phrase_ids"],[1,2]);self.assertEqual(p["scenes"][0]["timing"],"original_block_only")
    def test_other_subjects(self):
        self.assertIn("health",choose("O hospital tem pacientes.")["assets"])
        self.assertIn("food",choose("O arroz no supermercado.")["assets"])
        self.assertIn("transport",choose("O caminhão passou na estrada.")["assets"])
    def test_unknown(self):
        self.assertEqual(choose("Uma ideia abstrata.")["template"],"unresolved")
    def test_authored(self):
        self.assertEqual(choose("Uma ideia abstrata.",["clock"])["assets"],["clock"])
        with self.assertRaises(ValueError):choose("Teste",["nonexistent"])
    def test_identity(self):
        r,m,a=fixture(["Uma casa."]);a["audio_sha256"]="other"
        with self.assertRaises(ValueError):create_plan(r,m,a)
    def test_bad_caption(self):
        r,m,a=fixture(["Uma casa."]);a["candidate_cues"][0]["caption"]="Outra casa."
        with self.assertRaises(ValueError):create_plan(r,m,a)
    def test_no_lost_text(self):
        r,m,a=fixture(["Uma casa."]);m["blocks"][0]["spoken"]="Outro texto."
        with self.assertRaises(ValueError):create_plan(r,m,a)
    def test_no_invented_numbers(self):
        p=create_plan(*fixture(["O preço aumentou."]));self.assertEqual(p["scenes"][0]["visual_claims_added"],[])
    def test_bad_cue_fallback(self):
        r,m,a=fixture(["Uma casa.","Uma creche."]);a["candidate_cues"][1]["start"]=.5
        self.assertEqual(create_plan(r,m,a)["block_fallback_scenes"],1)
if __name__=="__main__":unittest.main()
