import unittest
from fatovia.local_draft import validate,quote_options

class DraftTests(unittest.TestCase):
    def test_grounding(self):
        source="Um texto de exemplo suficientemente longo."
        good={"titulo":"O que propõe o texto?","perguntas":["Qual é o objetivo?","O que falta esclarecer?","Como seria acompanhado?"],"citacao":source}
        self.assertEqual(validate(good,source),[])
        self.assertIn("quote_not_grounded",validate({**good,"citacao":"Uma frase inventada."},source))
        self.assertIn("duplicate_questions",validate({**good,"perguntas":["Qual é o objetivo?"]*3},source))
    def test_schema(self):
        self.assertEqual(validate({"publicar":True},""),["invalid_schema"])
    def test_quote_fragments(self):
        source=" ".join(["Palavras do documento oficial"]*30)
        self.assertTrue(all(fragment in source and len(fragment)<=220 for fragment in quote_options(source)))
