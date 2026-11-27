import unittest
from fatovia.reel_factory import build_plan, caption, select
from fatovia import multiformat as mf
from datetime import datetime, timezone
ITEM={"id":"camara:123","version":"a"*14,"title":"PL 123/2026","topics":["economia"],"public_url":"https://www.camara.leg.br/propostas-legislativas/123","source_url":"https://dadosabertos.camara.leg.br/api/v2/proposicoes/123","editorial_score":70}
REVIEW={"cards":[{"kind":k,"headline":h,"body":b} for k,h,b in [
("question","Como muda o imposto?","Uma proposta discute a tributação de um pagamento no Brasil."),
("proposal","O texto","O projeto pretende mudar a alíquota sobre uma modalidade de pagamento."),
("mechanism","Como funciona?","Se uma alíquota aumenta, a retenção inicial pode aumentar."),
("conditional","Na prática","Se aprovado, o texto pode alterar os valores, sem comprovar impacto final."),
("questions","O que falta?","Quem paga? Qual seria a alíquota?")]]}
class FactoryTests(unittest.TestCase):
    def test_caption_and_distinct_plans(self):
        p=build_plan(ITEM,REVIEW);self.assertEqual(p,build_plan(ITEM,REVIEW))
        self.assertIn("Quem paga?",p["caption"]);self.assertIn("Qual seria a alíquota?",p["caption"])
        self.assertIn("comentários",p["caption"]);self.assertEqual(p["caption"].count("#"),5)
        self.assertIn(ITEM["public_url"],p["caption"])
        self.assertEqual(len({x["kind"] for x in p["shots"]}),12)
        q=build_plan({**ITEM,"id":"camara:124","topics":["saude"]},REVIEW)
        self.assertNotEqual(p["seed"],q["seed"]);self.assertIn("#SaudePublica",q["caption"])
        self.assertEqual(p["status"],"draft_requires_independent_review")
    def test_selection_does_not_bypass_live_or_review(self):
        now=datetime.now(timezone.utc);s={"pending":[ITEM]}
        yes=lambda *a:True;no=lambda *a:False
        self.assertIsNone(select(s,now,yes,no,lambda _:REVIEW))
        self.assertIsNone(select(s,now,no,yes,lambda _:REVIEW))
        self.assertIsNone(select({**s,"published":[ITEM]},now,yes,yes,lambda _:REVIEW))
        self.assertIsNotNone(select(s,now,yes,yes,lambda _:REVIEW))
