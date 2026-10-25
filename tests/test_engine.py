import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fatovia.engine import choose, classify, daily_limit, from_camara, preferred_hours, validate_candidate
from fatovia.render import render

NOW = datetime(2026, 10, 25, 18, tzinfo=ZoneInfo("America/Fortaleza"))


def proposal():
    return from_camara(
        {"id": 1020304, "siglaTipo": "PL", "numero": 12, "ano": 2026,
         "ementa": "Dispõe sobre transparência dos indicadores de saúde e acesso público "
                   "a metodologias e relatórios de acompanhamento do Sistema Único de Saúde."},
        {"descricaoTramitacao": "Apresentação de proposição para análise inicial",
         "dataHora": "2026-10-25T10:00:00"}
    )


class EditorialTests(unittest.TestCase):
    def setUp(self):
        self.state = {"published": [], "pending": [], "metrics": []}

    def test_classificacao(self):
        self.assertIn("saude", classify("Atendimento de saúde no SUS"))

    def test_fonte_oficial(self):
        self.assertEqual(validate_candidate(proposal()), [])

    def test_fonte_nao_confiavel(self):
        item = proposal()
        item["source_url"] = "https://outro-site.example/noticia"
        self.assertTrue(validate_candidate(item))

    def test_duplicacao_pendente(self):
        item = proposal()
        self.assertEqual(len(choose([item], self.state, NOW)), 1)
        self.state["pending"].append(item)
        self.assertEqual(choose([item], self.state, NOW), [])

    def test_duplicacao_publicada(self):
        item = proposal()
        self.state["published"].append({**item, "published_at": NOW.isoformat()})
        self.assertEqual(choose([item], self.state, NOW), [])

    def test_frequencia_conservadora(self):
        self.assertEqual(daily_limit(self.state), 2)
        self.assertEqual(preferred_hours(self.state), [9, 19])

    def test_carrossel_sete_jpeg(self):
        item = proposal()
        with tempfile.TemporaryDirectory() as directory:
            render(item, directory)
            self.assertEqual(len(item["cards"]), 7)
            self.assertTrue(all(Path(p).read_bytes().startswith(b"\xff\xd8\xff") for p in item["cards"]))


if __name__ == "__main__":
    unittest.main()
