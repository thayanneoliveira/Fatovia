import unittest
from fatovia.local_draft import validate
class DraftTests(unittest.TestCase):
    def test_grounding(self):
        source="Um texto de exemplo suficientemente longo."
        questions=["Qual é o objetivo?","O que falta esclarecer?","Como seria acompanhado?"]
        self.assertEqual(validate({"perguntas":questions,"citacao":source},source),[])
        self.assertIn("quote_not_grounded",validate({"perguntas":questions,"citacao":"Uma frase inventada."},source))
    def test_schema(self):
        self.assertEqual(validate({"publicar":True},""),["invalid_schema"])
