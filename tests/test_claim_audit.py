import unittest
from fatovia.claim_audit import audit_draft

DOC={"title":"PL 12/2026","summary":"Propõe a redução de 60% das alíquotas.","stage":"Apresentação"}
BASE={"titulo":"O que a proposta altera?","perguntas":["Quem seria beneficiado?","Qual é o texto final?","Qual seria a regra?"],"citacao":DOC["summary"]}
class ClaimAuditTests(unittest.TestCase):
    def test_no_positive_authorization(self):
        r=audit_draft(BASE,DOC)
        self.assertEqual(r["decision"],"manual_review_required")
        self.assertFalse(r["publication_authorized"])
    def test_number_invented(self):
        r=audit_draft({**BASE,"titulo":"O desconto seria de 80%?"},DOC)
        self.assertIn("number_not_in_source",[f["code"] for f in r["findings"]])
    def test_legal_status(self):
        r=audit_draft({**BASE,"titulo":"O benefício já está em vigor?"},DOC)
        self.assertEqual(r["decision"],"rejected_by_rules")
    def test_loaded_question(self):
        r=audit_draft({**BASE,"titulo":"Por que o governo mentiu?"},DOC)
        self.assertIn("loaded_presupposition",[f["code"] for f in r["findings"]])
    def test_quote(self):
        self.assertEqual(audit_draft({**BASE,"citacao":"Aprovado."},DOC)["decision"],"rejected_by_rules")
    def test_number_matching_is_not_truth_validation(self):
        self.assertFalse(audit_draft({**BASE,"titulo":"O desconto seria de 60%?"},DOC)["publication_authorized"])
