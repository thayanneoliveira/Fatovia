import unittest
from datetime import datetime
from fatovia.engine import from_camara, choose
from fatovia.evidence import seal, sealed, verify_live, read_document
from fatovia.memory import duplicate

NOW=datetime.fromisoformat("2026-11-14T12:00:00-03:00")
RECORD={"id":12345,"siglaTipo":"PL","numero":12,"ano":2026,"ementa":"Dispõe sobre transparência de indicadores de saúde e acesso público a metodologias e relatórios de acompanhamento do Sistema Único de Saúde."}
STAGE={"descricaoTramitacao":"Apresentação para análise","dataHora":"2026-11-14"}
class GateTests(unittest.TestCase):
    def test_binding_and_tamper(self):
        item=from_camara(RECORD,STAGE)
        seal(item,NOW)
        self.assertTrue(sealed(item,NOW))
        item["caption"]="alterada"
        self.assertFalse(sealed(item,NOW))
    def test_live_source_changes(self):
        item=from_camara(RECORD,STAGE)
        def fetch(url,params=None):
            return {"dados":[STAGE]} if url.endswith("tramitacoes") else {"dados":RECORD}
        self.assertTrue(verify_live(item,fetch))
        item["summary"]+=" Mudança."
        self.assertFalse(verify_live(item,fetch))
    def test_detail_status_preferred(self):
        def fetch(url,params=None):
            if url.endswith("tramitacoes"):
                raise AssertionError("unneeded history")
            return {"dados":{**RECORD,"statusProposicao":STAGE}}
        detail,stage,method=read_document("https://dadosabertos.camara.leg.br/api/v2/proposicoes/12345",fetch)
        self.assertEqual(method,"detail_status")
        self.assertEqual(stage,STAGE)
        self.assertTrue(verify_live(from_camara(RECORD,STAGE),fetch))
    def test_identifier_mismatch(self):
        item=from_camara(RECORD,STAGE)
        item["source_url"]="https://dadosabertos.camara.leg.br/api/v2/proposicoes/99"
        with self.assertRaises(ValueError):
            seal(item,NOW)
    def test_duplicate_same_batch(self):
        one=from_camara(RECORD,STAGE)
        two=from_camara({**RECORD,"id":12346,"numero":13},STAGE)
        self.assertTrue(duplicate(one,two))
        self.assertEqual(len(choose([one,two],{},NOW)),1)
