import os
import tempfile
import unittest
from datetime import datetime,timedelta
from pathlib import Path
from fatovia.engine import from_camara
from fatovia.evidence import seal
from fatovia.render import render
from fatovia.editorial_audit import review,approved,POLICY

NOW=datetime.fromisoformat("2026-11-14T12:00:00-03:00")
class AuditTests(unittest.TestCase):
    def test_report_binds_bytes_and_expires(self):
        old=os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                item=from_camara({"id":12345,"siglaTipo":"PL","numero":12,"ano":2026,
                    "ementa":"Dispõe sobre transparência de indicadores de saúde e acesso a relatórios públicos."},
                    {"descricaoTramitacao":"Apresentação","dataHora":"2026-11-14"})
                render(item)
                seal(item,NOW)
                item["status"]="ready"
                row=review(item,NOW,source_check=lambda _:True)
                self.assertEqual(row["decision"],"approved_documentary_only")
                report={"policy":POLICY,"reviews":[row]}
                self.assertTrue(approved(item,NOW,report))
                self.assertFalse(approved(item,NOW+timedelta(hours=25),report))
                self.assertFalse(approved(item,NOW,{"policy":POLICY,"reviews":[]}))
                p=Path(item["cards"][0])
                p.write_bytes(p.read_bytes()+b"tamper")
                self.assertFalse(approved(item,NOW,report))
                self.assertEqual(review(item,NOW,source_check=lambda _:True)["decision"],"rejected")
                self.assertEqual(review(item,NOW,source_check=lambda _:False)["decision"],"rejected")
            finally:
                os.chdir(old)
