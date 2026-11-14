import unittest
import json
from datetime import date,datetime
from fatovia.budget import latest_due,parse,collect,stage_for

NOW=datetime.fromisoformat("2026-11-14T17:00:00-03:00")
ROW={"exercicio":2026,"periodo":4,"cod_ibge":1,"ente":"União","esfera":"U","anexo":"RREO-Anexo 01",
     "rotulo":"Despesas Orçamentárias","cod_conta":"example","conta":"Despesas correntes","coluna":"DESPESAS PAGAS ATÉ O BIMESTRE (j)","valor":123.45}
def payload(rows,more=False):
    return json.dumps({"items":rows,"hasMore":more}).encode()
class BudgetTests(unittest.TestCase):
    def test_period(self):
        self.assertEqual(latest_due(NOW.date())[:2],(2026,4))
        self.assertEqual(latest_due(date(2026,1,15))[:2],(2025,5))
    def test_distinct_stage(self):
        self.assertEqual(stage_for("DESPESAS EMPENHADAS ATÉ O BIMESTRE (f)"),"empenhado")
        self.assertIsNone(stage_for("DESPESAS EMPENHADAS NO BIMESTRE"))
    def test_amount_and_scope(self):
        out=parse(payload([ROW]),2026,4)
        self.assertEqual(out["cells"][0]["valor"],"123.45")
        self.assertEqual(out["cells"][0]["stage"],"pago")
        with self.assertRaises(ValueError):
            parse(payload([{**ROW,"cod_ibge":31}]),2026,4)
    def test_fail_incomplete(self):
        with self.assertRaises(ValueError):
            parse(payload([ROW],True),2026,4)
        with self.assertRaises(ValueError):
            parse(payload([ROW,ROW]),2026,4)
    def test_no_missing_zero(self):
        self.assertEqual(parse(payload([{**ROW,"valor":None}]),2026,4)["cells"],[])
    def test_no_automatic_authority(self):
        report=collect(NOW,lambda *args: payload([ROW]))
        self.assertFalse(report["publication_authorized"])
