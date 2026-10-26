"""Testes exclusivamente com objetos locais: jamais enviam POST ao Instagram."""
import copy
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import requests

from fatovia.engine import from_camara
from fatovia.publisher import (
    PublicationError, choose_due, config, deliver, marker, prepare, public_urls,
    qualified, reconcile, TARGET_USERNAME,
)

NOW = datetime.fromisoformat("2026-10-27T09:12:00-03:00")
CFG = {"enabled": True, "token": "FAKE_TEST_TOKEN", "ig_id": "17841434700481151",
       "base": "https://graph.instagram.com/v25.0"}


def item():
    doc = from_camara({
        "id": 1020304, "siglaTipo": "PL", "numero": 12, "ano": 2026,
        "ementa": "Dispõe sobre transparência dos indicadores de saúde e acesso público "
                  "a metodologias e relatórios de acompanhamento do Sistema Único de Saúde.",
    }, {"descricaoTramitacao": "Apresentação para análise inicial",
        "dataHora": "2026-10-25T10:00:00"})
    doc["status"] = "ready"
    doc["editorial_score"] = 90
    doc["cards"] = [f'docs/media/camara-1020304/{doc["version"]}/{i:02}.jpg'
                    for i in range(1, 8)]
    doc["caption"] = ("Documento legislativo registrado na Câmara, sem inferência de aprovação. "
                      "Consulte a fonte original para conferir o conteúdo e a tramitação.\n\n"
                      f'ID editorial: {doc["id"]}/{doc["version"]}')
    return doc


class FakeMeta:
    def __init__(self, existing=None, fail=False):
        self.create_calls = []
        self.existing_media = existing
        self.fail = fail
        self.published = []

    def account(self):
        return {"id": CFG["ig_id"], "username": TARGET_USERNAME}

    def existing(self, source):
        return self.existing_media

    def create(self, data):
        if self.fail:
            raise requests.Timeout("network timeout")
        self.create_calls.append(data)
        return str(len(self.create_calls) + 1000)

    def ready(self, parent):
        return None

    def publish(self, container):
        self.published.append(container)
        return "18100000000000000"

    def permalink(self, mid):
        return "https://www.instagram.com/p/testmock/"


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.state = {"blackout_dates": ["2026-10-25", "2026-10-26"],
                      "metrics": [], "published": [], "pending": [item()]}

    def test_tres_janelas_com_metricas_suficientes(self):
        from fatovia.engine import daily_limit, preferred_hours
        metrics = []
        for hour in (9, 14, 19):
            for i in range(15):
                metrics.append({"hour": hour, "reach": 100, "shares": 5, "saves": 5})
        self.state["metrics"] = metrics
        self.assertEqual(daily_limit(self.state), 3)
        hours = preferred_hours(self.state)
        self.assertEqual(len(hours), 3)
        self.assertTrue(all(b - a >= 4 for a, b in zip(hours, hours[1:])))

    def test_configuracao_meta_sem_host_expresso(self):
        import os
        from fatovia.publisher import config
        with patch.dict(os.environ, {"META_API_HOST": "", "META_GRAPH_VERSION": ""}):
            self.assertIn("graph.instagram.com/v25.0", config()["base"])

    def test_sem_publicacao_em_bloqueio(self):
        self.assertIsNone(choose_due(self.state, datetime.fromisoformat("2026-10-25T09:12:00-03:00")))

    def test_eligibilidade_com_proposta(self):
        self.assertTrue(qualified(self.state["pending"][0], NOW))

    def test_prioridade_e_horario(self):
        self.assertEqual(choose_due(self.state, NOW)["id"], "camara:1020304")
        self.assertIsNone(choose_due(self.state, datetime.fromisoformat("2026-10-27T11:12:00-03:00")))

    def test_urls_sao_publicas_e_unicas(self):
        urls = public_urls(self.state["pending"][0])
        self.assertEqual(len(urls), 7)
        self.assertTrue(all(url.startswith("https://thayanneoliveira.github.io/Fatovia/media/") for url in urls))

    def test_bloqueia_url_maliciosa(self):
        subject = item()
        subject["cards"][0] = "docs/media/../outside/01.jpg"
        with self.assertRaises(PublicationError):
            public_urls(subject)

    def test_bloqueia_tema_sensivel(self):
        subject = item()
        subject["summary"] = "Investigação criminal envolve denúncia de crime eleitoral"
        self.assertFalse(qualified(subject, NOW))

    def test_sem_credenciais_nao_prepara(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("fatovia.publisher.STATE_PATH", Path(folder) / "state.json"):
                result = prepare(self.state, NOW, {**CFG, "token": ""})
                self.assertEqual(result["action"], "missing_credentials")

    def test_prepara_transacao_sem_post(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("fatovia.publisher.STATE_PATH", Path(folder) / "state.json"):
                result = prepare(self.state, NOW, CFG)
                self.assertEqual(result["action"], "prepared")
                self.assertEqual(self.state["publishing"]["status"], "checkpointed")
                again = prepare(self.state, NOW, CFG)
                self.assertEqual(again["action"], "reconcile")

    def test_entrega_carrossel_sete_cards(self):
        meta = FakeMeta()
        with tempfile.TemporaryDirectory() as folder:
            with patch("fatovia.publisher.STATE_PATH", Path(folder) / "state.json"):
                prepare(self.state, NOW, CFG)
                with patch("fatovia.publisher.verify_media"):
                    result = deliver(self.state, NOW, CFG, client=meta)
        self.assertEqual(result["action"], "published")
        self.assertEqual(len(meta.create_calls), 8)
        self.assertEqual(meta.create_calls[-1]["media_type"], "CAROUSEL")
        self.assertEqual(len(self.state["published"]), 1)
        self.assertFalse(self.state["pending"])
        self.assertIsNone(self.state["publishing"])

    def test_conciliacao_encontra_post_e_nao_reenvia(self):
        meta = FakeMeta(existing={"id": "1812222222222",
                                  "permalink": "https://www.instagram.com/p/test/"})
        with tempfile.TemporaryDirectory() as folder:
            with patch("fatovia.publisher.STATE_PATH", Path(folder) / "state.json"):
                prepare(self.state, NOW, CFG)
                result = reconcile(self.state, NOW, CFG, client=meta)
        self.assertEqual(result["action"], "recovered")
        self.assertEqual(meta.create_calls, [])
        self.assertEqual(len(self.state["published"]), 1)

    def test_falha_ambigua_nao_republica(self):
        meta = FakeMeta(fail=True)
        with tempfile.TemporaryDirectory() as folder:
            with patch("fatovia.publisher.STATE_PATH", Path(folder) / "state.json"):
                prepare(self.state, NOW, CFG)
                with patch("fatovia.publisher.verify_media"):
                    with self.assertRaises(requests.Timeout):
                        deliver(self.state, NOW, CFG, client=meta)
                self.assertEqual(self.state["publishing"]["status"], "uncertain")
                again = prepare(self.state, NOW, CFG)
                self.assertEqual(again["action"], "reconcile")

    def test_post_ja_registrado_nao_e_repetido(self):
        self.state["published"].append({
            "id": item()["id"], "version": item()["version"],
            "published_at": "2026-10-25T09:00:00-03:00"
        })
        self.assertIsNone(choose_due(self.state, NOW))


if __name__ == "__main__":
    unittest.main()
