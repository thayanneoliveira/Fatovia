import copy, json, unittest
from editorial_engine import audit, fingerprint, prompt, STAGES, RUBRIC

def fixture():
    # Synthetic QA sample, not a publishable factual story.
    claims=[{"id":"c","kind":"hypothesis","text":"Uma obra pode atrasar.","disclosure":"Cenário hipotético."}]
    return {"id":"test","central_question":"Por que a obra atrasou?","audience_impact":"Serviço indisponível.",
      "beats":[{"stage":s,"narration":"Exemplo hipotético de uma obra.","claim_ids":["c"]} for s in STAGES],
      "claims":claims,"action":{"responsible":"Órgão responsável","question":"Qual prazo?","indicator":"Prazo","how":"Consultar contrato","url":"https://example.org/"},
      "tradeoff":"Tempo e custo","final_question":"O que foi entregue?"}
def review(d):
    return {"kind":"independent_editorial_review","reviewer":"synthetic","draft_sha256":fingerprint(d),"scores":dict.fromkeys(RUBRIC,5),
     "facts_verified":True,"neutrality_verified":True,"fiction_disclosed":True,"action_verified":True}

class EditorialTests(unittest.TestCase):
    def test_structure_never_publishes(self):
        d=fixture();self.assertEqual(audit(d)["status"],"needs_semantic_review");self.assertFalse(audit(d)["publish_allowed"])
    def test_review_bound_to_draft(self):
        d=fixture();r=review(d);self.assertEqual(audit(d,r)["status"],"editorial_candidate_only");self.assertFalse(audit(d,r)["publish_allowed"])
        d["beats"][0]["narration"]="Mudou";self.assertIn("stale_review",audit(d,r)["issues"])
    def test_missing_action(self):
        d=fixture();del d["action"];self.assertIn("non_verifiable_action",audit(d)["issues"])
    def test_missing_beat(self):
        d=fixture();d["beats"].pop();self.assertIn("missing_or_disordered_stages",audit(d)["issues"])
    def test_unsupported_fact(self):
        d=fixture();d["claims"][0]["kind"]="fact";self.assertIn("fact_without_evidence:c",audit(d)["issues"])
    def test_hidden_fiction(self):
        d=fixture();del d["claims"][0]["disclosure"];self.assertIn("undisclosed_example:c",audit(d)["issues"])
    def test_low_score(self):
        d=fixture();r=review(d);r["scores"]["retention"]=3;self.assertIn("rubric_below_threshold",audit(d,r)["issues"])
    def test_missing_neutrality(self):
        d=fixture();r=review(d);r["neutrality_verified"]=False;self.assertIn("semantic_gate_incomplete",audit(d,r)["issues"])
    def test_benchmark(self):
        from pathlib import Path
        b=json.loads(Path("benchmark_creche.json").read_text())
        self.assertEqual(b["review"]["sample_size"],1);self.assertIsNone(b["review"]["public_performance"]);self.assertEqual(sum(b["review"]["scores"].values()),30);self.assertTrue(b["script"])
    def test_prompt(self):
        self.assertIn("conhecimento prévio zero",prompt("saúde"))
if __name__=="__main__": unittest.main()
