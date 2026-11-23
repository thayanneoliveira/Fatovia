"""Testes exclusivamente com objetos locais: jamais enviam POST ao Instagram."""
import copy
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import requests

from fatovia.engine import from_camara
from fatovia.evidence import seal
from fatovia.publisher import (
    PublicationError, choose_due, config, deliver, marker, prepare, public_urls,
    qualified, reconcile, TARGET_USERNAME, MetaClient,
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
    seal(doc,NOW)
    return doc


class FakeMeta:
    def __init__(self, existing=None, fail=False):
        self.create_calls = []
        self.existing_media = existing
        self.fail = fail
        self.published = []

    def account(self):
        return {"id": "999999999999", "user_id": CFG["ig_id"], "username": TARGET_USERNAME}

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
        approval=patch("fatovia.publisher.approved",return_value=True)
        hosted=patch("fatovia.publisher.verify_hosted",return_value=True)
        pilot=patch("fatovia.publisher.pilot_allowed",return_value=True)
        pilot.start(); self.addCleanup(pilot.stop)
        approval.start(); hosted.start()
        self.addCleanup(approval.stop); self.addCleanup(hosted.stop)
        self.state = {"blackout_dates": ["2026-10-25", "2026-10-26"],
                      "metrics": [], "published": [], "pending": [item()]}

    def test_approved_content_does_not_expire_after_fourteen_days(self):
        from datetime import timedelta
        from fatovia.evidence import sealed
        source = self.state["pending"][0]
        later = NOW + timedelta(days=60)
        self.assertTrue(sealed(source, later))
        self.assertTrue(qualified(source, later))
        self.assertFalse(sealed(source, NOW - timedelta(seconds=1)))
        self.assertFalse(qualified(source, NOW - timedelta(seconds=1)))
        changed = copy.deepcopy(source)
        changed["summary"] = "Conteudo alterado apos aprovacao"
        self.assertFalse(sealed(changed, later))
        self.assertFalse(qualified(changed, later))

    def test_experimento_quatro_janelas_nao_muda_com_metricas(self):
        from fatovia.engine import daily_limit, preferred_hours
        metrics = []
        for hour in (9, 14, 19):
            for i in range(15):
                metrics.append({"hour": hour, "reach": 100, "shares": 5, "saves": 5})
        self.state["metrics"] = metrics
        self.assertEqual(daily_limit(self.state), 4)
        hours = preferred_hours(self.state)
        self.assertEqual(hours, [9, 13, 17, 21])
        self.assertTrue(all(b - a >= 4 for a, b in zip(hours, hours[1:])))

    def test_quatro_janelas_e_limite_diario(self):
        for i, hour in enumerate((9, 13, 17, 21)):
            now = datetime.fromisoformat(f"2026-10-27T{hour:02}:12:00-03:00")
            self.assertIsNotNone(choose_due(self.state, now))
            self.state["published"].append({"id": f"other:{i}", "version": "1",
                                            "published_at": now.isoformat()})
            self.assertIsNone(choose_due(self.state, now))
        self.assertEqual(len(self.state["published"]), 4)
        self.assertIsNone(choose_due(self.state, datetime.fromisoformat("2026-10-27T22:12:00-03:00")))

    def test_pilot_late_slot_and_no_double_post(self):
        later=NOW.replace(hour=10,minute=24)
        self.assertIsNotNone(choose_due(self.state,later,pilot_window=True))
        self.state["published"]=[{"id":"other:1","version":"v","published_at":NOW.isoformat()}]
        self.assertIsNone(choose_due(self.state,later,pilot_window=True))
        self.assertIsNotNone(choose_due(self.state,NOW.replace(hour=17),pilot_window=True))
        self.assertIsNone(choose_due(self.state,NOW.replace(hour=11),pilot_window=True))

    def test_pausa_minima_entre_posts(self):
        self.state["published"] = [{"id":"other:1","version":"1",
                                    "published_at":"2026-10-27T11:15:00-03:00"}]
        self.assertIsNone(choose_due(self.state, datetime.fromisoformat("2026-10-27T13:12:00-03:00")))

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

    def test_sem_parecer_independente_nao_prepara(self):
        with patch("fatovia.publisher.approved", return_value=False):
            result=prepare(self.state,NOW,CFG)
        self.assertEqual(result["action"],"idle")

    def test_piloto_bloqueado_nao_prepara(self):
        with patch("fatovia.publisher.pilot_allowed",return_value=False):
            self.assertEqual(prepare(self.state,NOW,CFG)["action"],"idle")

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
                    result = deliver(self.state, NOW, CFG, client=meta, source_check=lambda item: True)
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
                        deliver(self.state, NOW, CFG, client=meta, source_check=lambda item: True)
                self.assertEqual(self.state["publishing"]["status"], "uncertain")
                again = prepare(self.state, NOW, CFG)
                self.assertEqual(again["action"], "reconcile")

    def test_post_ja_registrado_nao_e_repetido(self):
        self.state["published"].append({
            "id": item()["id"], "version": item()["version"],
            "published_at": "2026-10-25T09:00:00-03:00"
        })
        self.assertIsNone(choose_due(self.state, NOW))



class MetaIdentityRegressionTests(unittest.TestCase):
    def test_instagram_login_uses_professional_user_id_not_app_scoped_id(self):
        client=MetaClient(CFG)
        payload={"id":"999999999999","user_id":CFG["ig_id"],"username":TARGET_USERNAME}
        with patch.object(client,"request",return_value=payload) as call:
            self.assertEqual(client.account(),payload)
            call.assert_called_once_with("GET","me",params={"fields":"user_id,username"})

    def test_username_alone_or_app_id_alone_is_not_authorization(self):
        client=MetaClient(CFG)
        for payload in ({"id":CFG["ig_id"],"username":TARGET_USERNAME},
                        {"user_id":"99999999","username":TARGET_USERNAME},
                        {"user_id":CFG["ig_id"],"username":"other_account"}):
            with patch.object(client,"request",return_value=payload):
                with self.assertRaises(PublicationError) as ctx:
                    client.account()
                self.assertEqual(ctx.exception.code,"meta_identity_mismatch")

    def test_history_missing_or_paginated_does_not_mean_absence(self):
        client=MetaClient(CFG)
        for payload in ({}, {"data":[],"paging":{"next":"https://example.invalid"}}):
            with patch.object(client,"request",return_value=payload):
                with self.assertRaises(PublicationError):
                    client.existing(item())
    def test_duplicate_exact_marker_is_blocked(self):
        client=MetaClient(CFG)
        doc=item()
        with patch.object(client,"request",return_value={"data":[{"id":"1","caption":marker(doc)},{"id":"2","caption":marker(doc)}]}):
            with self.assertRaises(PublicationError):
                client.existing(doc)

if __name__ == "__main__":
    unittest.main()
