"""Editorial brand acceptance tests for future automated carousels."""
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from fatovia.render import card


class FatoViaBrandTests(unittest.TestCase):
    def test_dark_green_cover_is_mandatory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"test.jpg"
            card(path, 1, "O que muda?", "Uma proposta não é uma entrega comprovada.", "Fonte na legenda.")
            with Image.open(path) as im:
                self.assertEqual(im.size, (1080, 1350))
                r, g, b = im.convert("RGB").getpixel((14, 400))
                self.assertLess(r, 40)
                self.assertGreater(g, 45)
                self.assertLess(b, 80)

    def test_long_factual_text_does_not_overflow(self):
        body = ("A aprovação formal não equivale à implementação nem aos resultados. ")*5
        with tempfile.TemporaryDirectory() as tmp:
            card(Path(tmp)/"test.jpg", 2, "Como acompanhar os indicadores públicos?", body, "Dados oficiais na legenda.")


if __name__=="__main__":
    unittest.main()
