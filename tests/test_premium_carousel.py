import json,os,tempfile,unittest
from datetime import datetime
from pathlib import Path
from PIL import Image
from fatovia.didactic import reviewed,MANIFEST
from fatovia.engine import classify,digest
from fatovia.render import render
from fatovia.evidence import seal
from fatovia.editorial_audit import review,approved,POLICY
from fatovia.premium_carousel import REVISION
from fatovia.publisher import marker

class PremiumTests(unittest.TestCase):
    def test_all_pending_migration_drafts_render_and_bind(self):
        root=MANIFEST.parent
        drafts=json.loads((root/"carousel_premium_drafts.json").read_text())["items"]
        rows=json.loads(MANIFEST.read_text())["items"]
        old=os.getcwd()
        with tempfile.TemporaryDirectory() as t:
            try:
                os.chdir(t)
                for draft in drafts:
                    row=next(r for r in rows if (r["id"],r["version"])==(draft["id"],draft["version"]))
                    item={k:row[k] for k in ("id","version","title","summary","stage","stage_date")}
                    ident=item["id"].split(":")[1]
                    item.update(topics=classify(item["summary"]),summary_hash=digest(item["summary"].casefold()),source_url="https://dadosabertos.camara.leg.br/api/v2/proposicoes/"+ident,public_url="https://www.camara.leg.br/propostas-legislativas/"+ident,status="ready")
                    self.assertIsNotNone(reviewed(item))
                    render(item,premium=True)
                    now=datetime.fromisoformat("2026-11-28T12:00:00-03:00")
                    seal(item,now)
                    self.assertEqual(item["template_revision"],REVISION)
                    self.assertTrue(marker(item).endswith("/"+REVISION))
                    self.assertEqual(len(item["cards"]),7)
                    for path in item["cards"]:
                        with Image.open(path) as im:self.assertEqual(im.size,(1080,1350))
                    result=review(item,now,source_check=lambda _:True)
                    self.assertEqual(result["decision"],"approved_documentary_only",result)
                    self.assertTrue(approved(item,now,{"policy":POLICY,"reviews":[result]}))
                    Path(item["cards"][0]).write_bytes(b"invalid")
                    self.assertFalse(approved(item,now,{"policy":POLICY,"reviews":[result]}))
            finally:os.chdir(old)
