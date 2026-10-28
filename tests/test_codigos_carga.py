"""Regression tests for load identifiers: leading zeros are meaningful formatting."""
import unittest
from auditoria.codigos import codigos_carga_conferem,codigo_carga_padronizado


class TestCodigosDeCarga(unittest.TestCase):
    def test_zero_inicial(self):
        self.assertTrue(codigos_carga_conferem(
            "071536090654939574197031","71536090654939574197031"))
    def test_dois_zeros(self):
        self.assertTrue(codigos_carga_conferem(
            "001234567890123456789012","1234567890123456789012"))
    def test_tres_zeros(self):
        self.assertTrue(codigos_carga_conferem(
            "000123456789012345678901","123456789012345678901"))
    def test_codigos_diferentes(self):
        self.assertFalse(codigos_carga_conferem(
            "071536090654939574197031","71536090654939574197032"))
    def test_nao_confundir_ausencia_com_zero(self):
        self.assertFalse(codigos_carga_conferem(None, "0"))
        self.assertFalse(codigos_carga_conferem("", "0"))
    def test_valores_invalidos(self):
        for v in ("-1","1.2","x123","123 ","1"*25, "", "  "):
            if v=="123 ":
                self.assertEqual(codigo_carga_padronizado(v),"0"*21+"123")
            else:
                self.assertIsNone(codigo_carga_padronizado(v))
    def test_rejeita_acima_24_digitos(self):
        self.assertIsNone(codigo_carga_padronizado("0"*25))


if __name__=="__main__":
    unittest.main()
