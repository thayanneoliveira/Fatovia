"""Testes unitários: soma de seções e interpretação de associação ecológica."""
import unittest
from auditoria.biometria_2026 import intfield

class TestCamposBU(unittest.TestCase):
    def test_inteiros_obrigatorios(self):
        self.assertEqual(intfield({"QT_COMPARECIMENTO":"00241"},"QT_COMPARECIMENTO"),241)
    def test_rejeita_negativo_e_texto(self):
        for value in ("", "-1", "NaN", "2,0", "  "):
            with self.assertRaises(ValueError):
                intfield({"QT_COMPARECIMENTO":value},"QT_COMPARECIMENTO")
    def test_zero_eh_valido(self):
        self.assertEqual(intfield({"QT_ELEI_BIOM_SEM_HABILITACAO":"0"},
                                  "QT_ELEI_BIOM_SEM_HABILITACAO"),0)

if __name__=="__main__":
    unittest.main()
