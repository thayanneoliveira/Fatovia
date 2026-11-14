import unittest
from fatovia.render import editorial_hook
from fatovia.engine import from_camara
from fatovia.claim_matrix import build
class HookTests(unittest.TestCase):
    def test_grounded_question(self):
        item=from_camara({"id":12345,"siglaTipo":"PL","numero":12,"ano":2026,"ementa":"Prevê medidas para médicos residentes e reajustes periódicos da bolsa de formação em saúde."},{"descricaoTramitacao":"Apresentação","dataHora":"2026-11-14"})
        title,anchors=editorial_hook(item)
        self.assertIn("médicos residentes",title)
        self.assertEqual(len(anchors),2)
        self.assertTrue(all(a in item["summary"] for a in anchors))
        rows=[r for r in build(item)["entries"] if r["type"]=="controlled_question_anchor"]
        self.assertEqual(len(rows),4)
    def test_no_unanchored_title(self):
        t,anchors=editorial_hook({"summary":"Apenas menciona médicos residentes."})
        self.assertEqual(anchors,[])
