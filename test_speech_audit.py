import unittest
from speech_audit import evaluate,tokens,edits
from pronunciation_prepare import prepare

def words(text):
    return [{"text":w,"start":i*.5,"end":i*.5+.4,"probability":.95} for i,w in enumerate(text.split())]
def audit(text,heard):
    return evaluate([{"caption":text}],words(heard),10.)
class SpeechTests(unittest.TestCase):
    def test_exact(self):
        r=audit("A casa ficou pronta.","A casa ficou pronta.");self.assertEqual(r["status"],"candidate_for_listening_review");self.assertFalse(r["publish_allowed"])
    def test_deletion(self):
        self.assertEqual(audit("A casa não ficou pronta.","A casa ficou pronta.")["counts"]["deletion"],1)
    def test_repeat(self):
        self.assertEqual(audit("A casa ficou pronta.","A casa casa ficou pronta.")["counts"]["insertion"],1)
    def test_substitution(self):
        self.assertEqual(audit("cem crianças","dez crianças")["counts"]["substitution"],1)
    def test_numeric(self):
        self.assertEqual(tokens("100 crianças"),tokens("cem crianças"));self.assertNotEqual(tokens("1,5"),tokens("15"));self.assertNotEqual(tokens("-5"),tokens("5"))
    def test_low_confidence(self):
        w=words("A casa");w[1]["probability"]=.2;r=evaluate([{"caption":"A casa"}],w,10.);self.assertEqual(r["status"],"needs_review");self.assertEqual(r["phrase_cue_count"],0)
    def test_missing_timing(self):
        w=words("A casa");w[1]["end"]=w[1]["start"];self.assertEqual(evaluate([{"caption":"A casa"}],w,10.)["status"],"needs_review")
    def test_approved_dictionary_only(self):
        dictionary={"entries":[{"written":"FatoVia","spoken":"Fato Via","status":"approved_in_episode"},{"written":"IBGE","spoken":"i bê gê é","status":"pending_listening"}]}
        result=prepare([{"caption":"FatoVia e IBGE"}],dictionary)[0]
        self.assertEqual(result["caption"],"FatoVia e IBGE");self.assertEqual(result["spoken"],"Fato Via e IBGE")
    def test_spoken_override(self):
        self.assertEqual(evaluate([{"caption":"100","spoken":"cem"}],words("cem"),10.)["wer"],0)
    def test_no_hallucinated_cues(self):
        r=audit("A casa ficou pronta.","A casa pronta.");self.assertFalse(r["candidate_cues"]);self.assertFalse(r["publish_allowed"])
if __name__=="__main__":unittest.main()
