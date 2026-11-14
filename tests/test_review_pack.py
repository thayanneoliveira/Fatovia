import os
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from fatovia.review_pack import visual_check,sheet
from fatovia.render import render
from fatovia.engine import from_camara

class ReviewPackTests(unittest.TestCase):
    def test_actual_jpeg_and_contact_sheet(self):
        old=os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                item=from_camara({"id":12345,"siglaTipo":"PL","numero":12,"ano":2026,
                    "ementa":"Dispõe sobre transparência de indicadores de saúde e acesso a relatórios públicos."},
                    {"descricaoTramitacao":"Apresentação","dataHora":"2026-11-14"})
                render(item)
                self.assertTrue(visual_check(item))
                sheet(item,Path("preview.png"))
                self.assertTrue(Path("preview.png").is_file())
                Image.new("RGB",(100,100)).save(item["cards"][0],"JPEG")
                self.assertFalse(visual_check(item))
            finally:
                os.chdir(old)
