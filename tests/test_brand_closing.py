import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from fatovia.brand import approved_logo,carousel_header
from fatovia.reel_closing import export

class BrandClosingTests(unittest.TestCase):
    def test_no_logo_no_substitute(self):
        with tempfile.TemporaryDirectory() as f:
            self.assertIsNone(approved_logo(Path(f)/"missing.json"))
            with patch("fatovia.reel_closing.approved_logo",return_value=None):
                with self.assertRaises(ValueError):export(Path(f)/"source.mp4",Path(f)/"out.mp4",1,"missing")
    def test_logo_exact_bytes(self):
        import os
        old=Path.cwd()
        with tempfile.TemporaryDirectory() as f:
            try:
                os.chdir(f);Path("assets").mkdir()
                logo=Path("assets/logo.png");Image.new("RGBA",(200,80),"#eed388").save(logo)
                policy=Path("p.json");policy.write_text(json.dumps({"approved_logo":{"path":str(logo),"sha256":hashlib.sha256(logo.read_bytes()).hexdigest()}}))
                mark=approved_logo(policy);self.assertIsNotNone(mark)
                picture=Image.new("RGB",(1080,1350),"#123E31")
                carousel_header(picture,mark)
                self.assertEqual(picture.getpixel((100,50)),(238,211,136))
                Image.new("RGBA",(200,80),"red").save(logo)
                self.assertIsNone(approved_logo(policy))
            finally:os.chdir(old)
if __name__=="__main__":unittest.main()
