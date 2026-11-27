import unittest,hashlib
from fatovia.free_tier import permitted
from fatovia.narration import MODEL,VOICE
class FreeTierTests(unittest.TestCase):
    def setUp(self):
        self.key="x"*30+"test"
        self.row={"schema":1,"status":"verified_free_tier","project":"FatoVia-TTS","billing":"not_configured_as_shown","max_spend_brl":0,"model":MODEL,"voice":VOICE,"key_suffix_sha256":hashlib.sha256(b"test").hexdigest()}
    def test_confirmed(self):self.assertTrue(permitted(self.row,self.key))
    def test_wrong_key(self):self.assertFalse(permitted(self.row,self.key+"x"))
    def test_revocation(self):self.assertFalse(permitted({**self.row,"status":"revoked"},self.key))
    def test_explicit_veto(self):self.assertFalse(permitted(self.row,self.key,"false"))
    def test_billing(self):self.assertFalse(permitted({**self.row,"billing":"enabled"},self.key))
    def test_empty(self):self.assertFalse(permitted(self.row,""))

    def test_owner_confirmed_mask_ambiguity(self):
        row={**self.row,"mask_alternatives_owner_confirmed":True,"mask_alternative_sha256":[hashlib.sha256(b"tEst").hexdigest()]}
        self.assertTrue(permitted(row,"AQ."+"x"*30+"tEst"))
        self.assertFalse(permitted(row,"AQ."+"x"*30+"other"))
        self.assertFalse(permitted(row,"AQ."+"x"*30+"tEst","false"))
        self.assertFalse(permitted({**row,"mask_alternatives_owner_confirmed":False},"AQ."+"x"*30+"tEst"))
    def test_reject_unbounded_alternatives(self):
        self.assertFalse(permitted({**self.row,"mask_alternatives_owner_confirmed":True,"mask_alternative_sha256":["a"*64]*4},self.key))
