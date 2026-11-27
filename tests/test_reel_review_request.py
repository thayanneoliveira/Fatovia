import unittest
from datetime import datetime, timezone, timedelta
from fatovia.reel_review_request import validate, provenance, REVIEW_FIELDS
class ReviewRequestTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime.now(timezone.utc)
        self.row={"run_id":123,"scope":"independent_final_media","reviewer":"independent test","checked_at":self.now.isoformat(),"review_evidence":{k:"test evidence" for k in REVIEW_FIELDS},**{k:"approved" for k in REVIEW_FIELDS},**{k:"a"*64 for k in ("video_sha256","script_sha256","caption_sha256","logo_sha256")}}
    def test_valid(self):self.assertEqual(validate(self.row,self.now),self.row)
    def test_no_self_attestation_without_evidence(self):
        with self.assertRaises(ValueError):validate({**self.row,"review_evidence":{}},self.now)
    def test_no_unreviewed_media(self):
        with self.assertRaises(ValueError):validate({**self.row,"visual_review":"pending"},self.now)
    def test_stale(self):
        with self.assertRaises(ValueError):validate({**self.row,"checked_at":(self.now-timedelta(days=2)).isoformat()},self.now)
    def test_provenance(self):
        r={"head_branch":"main","status":"completed","conclusion":"success","path":".github/workflows/reel-factory.yml","head_repository":{"full_name":"thayanneoliveira/Fatovia"}}
        provenance(r)
        for change in ({"head_branch":"lab"},{"conclusion":"failure"},{"head_repository":{"full_name":"fork/Fatovia"}}):
            with self.assertRaises(ValueError):provenance({**r,**change})
