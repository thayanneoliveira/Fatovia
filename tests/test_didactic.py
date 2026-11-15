import copy,json,unittest
from datetime import datetime
from unittest.mock import patch
from fatovia.didactic import reviewed,MANIFEST,REVISION
from fatovia.render import cards_for
from fatovia.claim_matrix import build
from fatovia.pilot import allowed
from fatovia.publisher import marker,choose_due

class DidacticTests(unittest.TestCase):
    def fixture(self,row):
        i={k:row[k] for k in ("id","version","title","summary","stage","stage_date")}
        i.update(source_url="https://dadosabertos.camara.leg.br/api/v2/proposicoes/"+row["id"].split(":")[1],
                 public_url="https://www.camara.leg.br/propostas-legislativas/"+row["id"].split(":")[1],template_revision=REVISION)
        return i
    def test_all_eight_reviewed_and_complete(self):
        bundle=json.loads(MANIFEST.read_text())
        self.assertEqual(len(bundle["items"]),8)
        for row in bundle["items"]:
            i=self.fixture(row)
            self.assertIsNotNone(reviewed(i))
            cards=cards_for(i)
            self.assertEqual(len(cards),7)
            self.assertNotIn("O restante da ementa",[c[0] for c in cards])
            self.assertIn("reviewed_conditional",{r["type"] for r in build(i)["entries"]})
            self.assertNotIn(r"\n",cards[6][1])
            self.assertTrue(marker(i).endswith("/didactic-v4"))
    def test_source_change_refuses_review(self):
        row=json.loads(MANIFEST.read_text())["items"][0]
        i=self.fixture(row)
        i["summary"]+=" Mudança não revisada."
        with self.assertRaises(ValueError):
            reviewed(i)
    def test_extended_slot_only_verified_replacement(self):
        row=json.loads(MANIFEST.read_text())["items"][0]
        i=self.fixture(row)
        policy={"schema":1,"status":"prepared","start_date":"2026-11-15","end_date":"2026-11-21","max_total":4,"max_daily":2,"allowed_hours":[9,17],"template_revision":REVISION,
                "items":[{"id":i["id"],"version":i["version"],"content_sha256":"x","card_sha256":["a"]*7}]}
        now=datetime.fromisoformat("2026-11-15T12:20:00-03:00")
        state={"published":[],"replacement_request":{"id":i["id"],"version":i["version"],"status":"awaiting_deletion"}}
        with patch("fatovia.pilot.fingerprint",return_value="x"),patch("fatovia.pilot.inspect_files",return_value=["a"]*7):
            self.assertFalse(allowed(state,i,now,policy))
            state["replacement_request"]["status"]="deletion_verified"
            self.assertTrue(allowed(state,i,now,policy))
            self.assertFalse(allowed(state,i,now.replace(day=16),policy))
