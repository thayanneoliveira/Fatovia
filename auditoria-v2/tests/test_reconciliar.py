"""Testes sintéticos: verificam cobertura, diferenças completas e falhas fechadas."""
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("audit_v2", HERE / "reconciliar_secoes.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

HEADER = "CD_MUNICIPIO;NR_ZONA;NR_SECAO;NR_URNA_ESPERADA"
HEADER_E = "CD_MUNICIPIO;NR_ZONA;NR_SECAO;NR_URNA_EFETIVADA"

def create_source(root, uf, kind, sections, corrupted=False):
    p = root / audit.PATTERNS[kind].format(uf=uf)
    header = HEADER if kind in ("24", "25") else HEADER_E
    lines = [header] + [f"{mun};{zone};{sec};{urn}" for mun, zone, sec, urn in sections]
    csv = "\n".join(lines) + "\n"
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"csec_{uf}.csv" if kind in ("24", "25") else f"result_{uf}.csv", csv)
    official = hashlib.sha512(p.read_bytes()).hexdigest()
    (root / (p.name + ".sha512")).write_text(official if not corrupted else ("0" * 128))
    return p

class ReconciliacaoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "dados"
        self.root.mkdir()
        self.out = Path(self.tmp.name) / "saida"
        self.s24 = [("1", "2", "3", "111"), ("1", "2", "4", "222")]
        self.s25 = [("1", "2", "3", "111"), ("1", "2", "4", "333"), ("1", "2", "5", "444")]
        self.sef = [("1", "2", "3", "111"), ("1", "2", "4", "333"), ("1", "2", "5", "555")]
        for k, rows in [("24", self.s24), ("25", self.s25), ("efetivada", self.sef), ("bu", self.sef * 2)]:
            create_source(self.root, "AC", k, rows)

    def test_completa_todas_diferencas(self):
        self.assertEqual(audit.run(self.root, self.out, ["AC"]), 0)
        result = json.loads((self.out / "manifesto_validacao.json").read_text())
        self.assertEqual(result["status"], "COMPLETE_FOR_IDENTIFIER_COMPARISONS")
        self.assertEqual(result["matrix_rows"], 3)
        self.assertEqual(result["coverage"]["AC/24_vs_25"]["somente_posterior"], 1)
        self.assertEqual(result["coverage"]["AC/24_vs_25"]["urna_divergente"], 1)
        self.assertEqual(result["coverage"]["AC/25_vs_efetivada"]["urna_divergente"], 1)
        self.assertEqual(result["coverage"]["AC/efetivada_vs_bu"]["urna_divergente"], 0)
        self.assertTrue((self.out / "matriz_completa_secoes.csv").exists())

    def test_falha_hash_bloqueia_resultado(self):
        p = self.root / audit.PATTERNS["25"].format(uf="AC")
        (self.root / (p.name + ".sha512")).write_text("0" * 128)
        self.assertEqual(audit.run(self.root, self.out, ["AC"]), 2)
        self.assertFalse((self.out / "matriz_completa_secoes.csv").exists())
        self.assertTrue(json.loads((self.out / "manifesto_validacao.json").read_text())["errors"])

    def test_falta_de_uf_nao_passa(self):
        self.assertEqual(audit.run(self.root, self.out, ["AC", "MG"]), 2)
        status = json.loads((self.out / "manifesto_validacao.json").read_text())
        self.assertEqual(status["coverage"]["MG"]["status"], "BLOCKED")

    def test_conflito_urna_mesma_secao_eh_bloqueante(self):
        p = self.root / audit.PATTERNS["bu"].format(uf="AC")
        create_source(self.root, "AC", "bu", self.sef + [("1", "2", "5", "999")])
        self.assertEqual(audit.run(self.root, self.out, ["AC"]), 2)
        self.assertFalse((self.out / "matriz_completa_secoes.csv").exists())

if __name__ == "__main__":
    unittest.main()
