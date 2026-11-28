import copy,json,os,tempfile,unittest
from datetime import datetime
from pathlib import Path
from fatovia.civic import make,valid,fresh,verify,flags,cards,SPECS
from fatovia.engine import from_camara,validate_candidate
from fatovia.evidence import seal,sealed
from fatovia.render import render
from fatovia.editorial_audit import review,approved,POLICY
from fatovia.publisher import qualified,marker
from fatovia.premium_carousel import REVISION

NOW=datetime.fromisoformat("2026-11-28T12:00:00-03:00")
class CivicTests(unittest.TestCase):
    def test_source_schema_and_same_value_no_daily_repeat(self):
        a=make("selic",{"period":"2026-11-27","value":"13.75"})
        b=make("selic",{"period":"2026-11-28","value":"13.750"})
        self.assertEqual(a["version"],b["version"])
        raw=json.dumps([{"data":"27/11/2026","valor":"13.75"},{"data":"28/11/2026","valor":"13.75"}]).encode()
        self.assertTrue(verify(a,NOW,lambda *args:raw))
        forged=make("selic",{"period":"2026-11-26","value":"13.75"})
        self.assertFalse(verify(forged,NOW,lambda *args:raw))
        self.assertFalse(verify(a,NOW,lambda *args:json.dumps([{"data":"28/11/2026","valor":"14"}]).encode()))
        a["source_url"]="https://example.org"
        self.assertFalse(valid(a))
    def test_aneel_current_month_only(self):
        raw=b"DatCompetencia;NomBandeiraAcionada\n2026-10-01;Amarela\n2026-11-01;Verde\n"
        self.assertEqual(flags(raw,NOW),[{"period":"2026-11","value":"verde"}])
        item=make("energia",{"period":"2026-11","value":"verde"})
        self.assertTrue(verify(item,NOW,lambda *a:raw))
        self.assertFalse(fresh(item,NOW.replace(month=12,day=1)))
        with self.assertRaises(ValueError):flags(b"DatCompetencia;NomBandeiraAcionada\n2026-10-01;Verde\n",NOW)
    def test_all_premium_reconstruct_and_tamper(self):
        old=os.getcwd()
        with tempfile.TemporaryDirectory() as t:
            try:
                os.chdir(t)
                items=[make("selic",{"period":"2026-11-27","value":"13.75"}),make("ipca",{"period":"2026-10","value":"0.14"}),make("emprego",{"period":"2026-Q3","value":"5.2"}),make("energia",{"period":"2026-11","value":"verde"})]
                items.append(from_camara({"id":123456,"siglaTipo":"PL","numero":123,"ano":2026,"ementa":"Dispõe sobre transparência de indicadores de saúde e acesso a relatórios públicos para acompanhamento das políticas públicas."},{"descricaoTramitacao":"Apresentação","dataHora":"2026-11-27"}))
                for item in items:
                    render(item,premium=True)
                    seal(item,NOW);item["status"]="ready"
                    self.assertEqual(item["template_revision"],REVISION)
                    self.assertIn(marker(item),item["caption"].splitlines())
                    self.assertTrue(qualified(item,NOW),item)
                    row=review(item,NOW,source_check=lambda _:True)
                    self.assertEqual(row["decision"],"approved_documentary_only",row)
                    self.assertTrue(approved(item,NOW,{"policy":POLICY,"reviews":[row]}))
                    self.assertEqual(len(item["cards"]),7)
                    self.assertFalse(review(item,NOW,source_check=lambda _:False)["decision"]=="approved_documentary_only")
                    Path(item["cards"][0]).write_bytes(b"tamper")
                    self.assertFalse(approved(item,NOW,{"policy":POLICY,"reviews":[row]}))
            finally:os.chdir(old)
