import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fatovia.engine import choose

class ExploreSignalTests(unittest.TestCase):
    def test_signal_breaks_tie_but_never_bypasses_gate(self):
        now = datetime(2026, 11, 14, 12, tzinfo=ZoneInfo("America/Fortaleza"))
        def item(i, topic, valid=True):
            summaries = {"saude":"Indicadores de saúde e atendimento nas unidades públicas, incluindo dados sobre filas, consultas e hospitais.", "economia":"Indicadores de renda e transparência fiscal, incluindo dados sobre orçamento, despesas e tributos públicos."}
            return {"id": "camara:"+str(i), "version":"v1", "title":"PL 1/2026",
                    "summary":summaries[topic],
                    "summary_hash":str(i), "source_url":"https://dadosabertos.camara.leg.br/api/v2/proposicoes/"+str(i) if valid else "https://example.org/",
                    "public_url":"https://www.camara.leg.br/propostas-legislativas/"+str(i),
                    "stage":"Registro oficial", "stage_date":now.date().isoformat(), "topics":[topic]}
        items=[item(1,"saude"),item(2,"economia"),item(3,"economia",False)]
        signal={"source":"manual_explore","topic":"economia","url":"https://www.instagram.com/p/ABCD1234/","observed_at":now.isoformat()}
        state={"explore_signals":[signal,dict(signal)]}
        selected=choose(items,state,now)
        self.assertEqual([x["id"] for x in selected],["camara:2","camara:1"])
        self.assertEqual(selected[0]["explore_signal_count"],1)
        state["explore_signals"][0]["observed_at"]=(now-timedelta(days=8)).isoformat()
        state["explore_signals"][1]["observed_at"]=(now-timedelta(days=8)).isoformat()
        self.assertEqual(choose(items,state,now)[0]["id"],"camara:1")
