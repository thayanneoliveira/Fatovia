"""Testes locais/offline: nunca usam dados eleitorais reais como fixtures."""
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from auditoria import tse
from auditoria.__main__ import consolidate, markdown_report, save


HEADERS = ["NR_TURNO", "SG_UF", "CD_MUNICIPIO", "NR_ZONA",
           "NR_SECAO", "NR_VOTAVEL", "QT_VOTOS", "QT_COMPARECIMENTO",
           "CD_CARGO_PERGUNTA", "DS_CARGO_PERGUNTA"]


def fixture(tmp, rows):
    path = Path(tmp) / "bu.zip"
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=HEADERS, delimiter=";", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zipout:
        zipout.writestr("bweb_2t_MA.csv", out.getvalue().encode("utf-8"))
    return path


def row(votable="13", votes="3", turnout="5", section="1", cargo="1", turno="2"):
    return dict(NR_TURNO=turno, SG_UF="MA", CD_MUNICIPIO="1234", NR_ZONA="1",
                NR_SECAO=section, NR_VOTAVEL=votable, QT_VOTOS=votes,
                QT_COMPARECIMENTO=turnout, CD_CARGO_PERGUNTA=cargo,
                DS_CARGO_PERGUNTA="Presidente" if cargo == "1" else "Governador")


class TestBU(unittest.TestCase):
    def test_soma_valida_e_filtros(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = fixture(tmp, [row(), row("22", "1"), row("95", "1"),
                                 row("99", "500", cargo="3"), row("22", "3", turno="1")])
            result = tse.count_bu("MA", path)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["secoes"], 1)
        self.assertEqual(result["total_votos"], 5)
        self.assertEqual(result["votos"], {"13": 3, "22": 1, "95": 1})

    def test_inconsistencia_de_comparecimento(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = fixture(tmp, [row(), row("22", "1")])
            r = tse.count_bu("MA", path)
        self.assertEqual(r["status"], "INCONSISTENTE")
        self.assertEqual(r["secoes_divergentes"], 1)

    def test_voto_duplicado_nao_soma_duas_vezes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = fixture(tmp, [row(), row(), row("22", "2")])
            r = tse.count_bu("MA", path)
        self.assertEqual(r["status"], "INCONSISTENTE")
        self.assertEqual(r["total_votos"], 5)
        self.assertIn("votavel_duplicado", [i["tipo"] for i in r["ocorrencias_amostra"]])

    def test_uf_incorreta_falha(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = fixture(tmp, [row()])
            with self.assertRaises(ValueError):
                tse.count_bu("SP", path)

    def test_sha512_e_validacao_de_catalogo(self):
        digest = hashlib.sha512(b"arquivo").hexdigest()
        resources = [
            {"id": "a", "name": "MA - Boletim de Urna - Segundo turno - 26.10.2026",
             "url": "https://cdn.tse.jus.br/arquivo.zip"},
            {"id": "b", "name": "MA - Hash SHA2 - Segundo turno - 26.10.2026",
             "url": "https://cdn.tse.jus.br/arquivo.zip.sha512"},
            {"id": "c", "name": "MA - Boletim de Urna - Primeiro turno",
             "url": "https://cdn.tse.jus.br/arquivo1.zip"},
        ]
        bu, sha = tse.bu_resources("MA", resources)
        self.assertEqual(bu["id"], "a")
        self.assertEqual(sha["id"], "b")
        original = tse.fetch
        try:
            tse.fetch = lambda *args, **kwargs: (digest + "  arquivo.zip\n").encode()
            self.assertEqual(tse.sha512_expected(sha["url"]), digest)
        finally:
            tse.fetch = original
        resources[0]["url"] = "https://example.com/arquivo.zip"
        with self.assertRaises(ValueError):
            tse.bu_resources("MA", resources)

    def test_referencia_agrega_sem_multiplos_csvs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = fixture(tmp, [row(), row("22", "2"), row("22", "8", turno="1")])
            self.assertEqual(tse.count_official(path), {("MA", "13"): 3, ("MA", "22"): 2})


class TestConsolidacao(unittest.TestCase):
    def make_states(self, directory):
        for uf in tse.UFS:
            save(Path(directory) / (uf + ".json"), {
                "uf": uf, "status": "OK", "hash_conferido": True,
                "secoes": 1, "votos": {"13": 3, "22": 2},
            })

    def expected(self):
        return ({(uf, candidate): value
                 for uf in tse.UFS for candidate, value in (("13", 3), ("22", 2))},
                {"url": "https://cdn.tse.jus.br/referencia.zip"})

    def test_todos_ufs_mesmos_totais(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_states(tmp)
            report = consolidate(tmp, reference_loader=self.expected)
        self.assertEqual(report["status"], "CONFERENCIA_CONSISTENTE")
        self.assertEqual(report["total_secoes_conferidas"], 28)
        self.assertEqual(report["totais_recontados_por_numero"], {"13": 84, "22": 56})
        self.assertIn("Conferência consistente", markdown_report(report))

    def test_diferenca_com_referencia(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_states(tmp)
            def tampered():
                exp, info = self.expected()
                exp[("MA", "13")] = 4
                return exp, info
            report = consolidate(tmp, reference_loader=tampered)
        self.assertEqual(report["status"], "DIVERGENCIAS_DE_TOTALIZACAO")
        self.assertEqual(report["diferencas_com_referencia"][0]["uf"], "MA")

    def test_uf_faltando_nao_passa(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_states(tmp)
            (Path(tmp) / "ZZ.json").unlink()
            report = consolidate(tmp, reference_loader=lambda: self.fail("referência não deve baixar"))
        self.assertEqual(report["status"], "INCONCLUSIVO")
        self.assertEqual(report["ufs_ausentes"], ["ZZ"])

    def test_hash_nao_conferido_nao_passa(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_states(tmp)
            save(Path(tmp) / "MA.json", {"uf": "MA", "status": "OK",
                                        "hash_conferido": False, "votos": {"13": 99}})
            report = consolidate(tmp, reference_loader=lambda: self.fail("referência não deve baixar"))
        self.assertEqual(report["status"], "INCONCLUSIVO")
        self.assertIn("MA", report["ufs_com_erro"])


if __name__ == "__main__":
    unittest.main()
