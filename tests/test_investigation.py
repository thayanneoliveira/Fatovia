import unittest
from datetime import datetime
from fatovia.investigation import build,budget_evidence
NOW=datetime.fromisoformat("2026-11-14T17:00:00-03:00")
STAMP=NOW.isoformat()
def series(periods, name="IPCA"):
    return {"status":"ok","response_sha256":"a"*64,"label":name,"unit":"%","frequency":"monthly","source_url":"https://example.invalid","limitation":"fixture",
            "observations":[{"period":p,"value":v} for p,v in periods]}
class InvestigationTests(unittest.TestCase):
    def test_only_common_period(self):
        b={"generated_at":STAMP,"series":{"16122":series([("2026-09","0.3"),("2026-10","0.4")])}}
        i={"generated_at":STAMP,"series":{"ipca_monthly":series([("2026-09","0.2")])}}
        r=build(b,i,{},NOW)
        self.assertEqual([x["period"] for x in r["dossiers"][0]["evidence"]],["2026-09","2026-09"])
        self.assertFalse(r["publication_authorized"])
    def test_budget_exact_account(self):
        cells=[{"cod_conta":"DespesasExcetoIntraOrcamentarias","rotulo":"Padrão","stage":s,"valor":v,"unit":"BRL_reported","coluna":s} for s,v in [("dotacao_atualizada","100"),("empenhado","70"),("liquidado","60"),("pago","50")]]
        report={"generated_at":STAMP,"entity":"União","status":"ok","response_sha256":"a"*64,"cells":cells,"period_end":"2026-08-31","source_url":"https://example.invalid","query_params":{}}
        self.assertEqual(budget_evidence(report,NOW)[-1]["value"],"50.00")
        self.assertEqual(budget_evidence({**report,"cells":cells+cells},NOW),[])
    def test_stale_not_used(self):
        self.assertEqual(build({"generated_at":"2025-01-01T00:00:00-03:00"},{},{},NOW)["dossiers"],[])
