import unittest
from fatovia.engine import from_camara
from fatovia.claim_matrix import build,digest,draft_matrix

def fixture(summary=None):
    return from_camara({"id":12345,"siglaTipo":"PL","numero":12,"ano":2026,
        "ementa":summary or "Dispõe sobre transparência de indicadores de saúde e acesso a relatórios públicos."},
        {"descricaoTramitacao":"Apresentação","dataHora":"2026-11-14"})

class MatrixTests(unittest.TestCase):
    def test_coverage(self):
        item=fixture()
        matrix=build(item)
        self.assertEqual({r["location"] for r in matrix["entries"]},{"card_01","card_02","card_03","card_04","card_05","card_06","card_07","caption"})
        for row in matrix["entries"]:
            evidence=row["evidence"]
            if evidence:
                self.assertEqual(item[evidence["field"]][evidence["start"]:evidence["end"]],evidence["excerpt"])
        self.assertIn("causality",matrix["unverified_dimensions"])
    def test_split_coverage(self):
        item=fixture(" ".join(["Indicadores de saúde e relatórios públicos"]*10))
        matrix=build(item)
        self.assertEqual(" ".join(r["text"] for r in matrix["entries"] if r["type"]=="attributed_excerpt"),item["summary"])
    def test_tampered_document_ref(self):
        item=fixture()
        item["source_url"]="https://example.org"
        with self.assertRaises(ValueError):
            build(item)
    def test_truncated_stage_refused(self):
        item=fixture()
        item["stage"]="Texto "*100
        with self.assertRaises(ValueError):
            build(item)
    def test_draft_never_approved(self):
        doc=fixture()
        rows=draft_matrix({"titulo":"A lei já vale?","perguntas":["O que mudou?"],"citacao":doc["summary"]},doc)
        self.assertEqual(rows[0]["decision"],"requires_semantic_review")
        self.assertEqual(rows[-1]["decision"],"literal_match_only")
