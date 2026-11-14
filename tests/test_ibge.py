import json
import unittest
from datetime import datetime
from fatovia.ibge import SPECS,parse,collect

NOW=datetime.fromisoformat("2026-11-14T17:00:00-03:00")
HEADER={"D1N":"Brasil","D2N":"Variável","D3N":"Mês","MN":"Unidade de Medida","V":"Valor"}
ROW={"D1C":"1","D1N":"Brasil","D2C":"63","D2N":"IPCA - Variação mensal","D3C":"202610","D3N":"outubro 2026","MN":"%","V":"0.45"}
def body(*rows,header=HEADER):
    return json.dumps([header,*rows]).encode()

class IbgeTests(unittest.TestCase):
    def test_metric_and_scope(self):
        r=parse(body(ROW),SPECS["ipca_monthly"],NOW)
        self.assertEqual(r["status"],"ok")
        self.assertEqual(r["observations"][0]["value"],"0.45")
        for field,value in [("D1C","31"),("D2C","2265"),("MN","Mil pessoas"),("D3C","202612")]:
            with self.assertRaises(ValueError):
                parse(body({**ROW,field:value}),SPECS["ipca_monthly"],NOW)
    def test_missing_not_zero(self):
        r=parse(body({**ROW,"V":"..."}),SPECS["ipca_monthly"],NOW)
        self.assertEqual(r["observations"],[])
        self.assertEqual(r["missing_periods"],["2026-10"])
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            parse(body(ROW,ROW),SPECS["ipca_monthly"],NOW)
    def test_quarterly(self):
        row={**ROW,"D2C":"4099","D2N":"Taxa de desocupação","D3C":"202603","D3N":"3º trimestre 2026","V":"6.0"}
        r=parse(body(row,header={**HEADER,"D3N":"Trimestre"}),SPECS["unemployment_quarterly"],NOW)
        self.assertEqual(r["observations"][0]["period"],"2026-Q3")
    def test_context_only(self):
        def fail(*args): raise TimeoutError()
        r=collect(NOW,fail)
        self.assertFalse(r["publication_authorized"])
        self.assertTrue(all(x["status"]=="unavailable" for x in r["series"].values()))
