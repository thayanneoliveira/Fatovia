import base64
import io
import json
import tempfile
import unittest
import wave
from urllib.error import HTTPError
from unittest.mock import Mock
from fatovia import narration as n

def wav(silent=False):
    b=io.BytesIO()
    with wave.open(b,"wb") as w:
        w.setparams((1,2,24000,0,"NONE","not compressed"))
        w.writeframes((b"\x00\x00" if silent else b"\x00\x10")*24000)
    return b.getvalue()

def response(raw):
    return io.BytesIO(json.dumps({"status":"completed","steps":[{"type":"model_output",
        "content":[{"type":"audio","data":base64.b64encode(raw).decode()}]}]}).encode())

class NarrationTests(unittest.TestCase):
    def test_separate_style_and_verbatim_script(self):
        p=n.payload("O que acontece?","Curious")
        self.assertEqual(p["input"][0]["content"][0]["text"],"O que acontece?")
        self.assertEqual(p["input"][0]["content"][0]["annotations"][0]["style"],"Curious")
        self.assertEqual(p["generation_config"]["speech_config"],[{"voice":"Algenib"}])
    def test_no_request_without_free_tier_or_key(self):
        with tempfile.TemporaryDirectory() as t:
            op=Mock()
            for env in ({},{"FATOVIA_GEMINI_FREE_TIER_VERIFIED":"true"}):
                with self.assertRaises(n.NarrationError):
                    n.generate("Teste",t,env=env,opener=op)
            op.assert_not_called()
    def test_cache_prevents_duplicate_requests(self):
        with tempfile.TemporaryDirectory() as t:
            op=Mock(return_value=response(wav()))
            env={"FATOVIA_GEMINI_FREE_TIER_VERIFIED":"true","FATOVIA_GEMINI_API_KEY":"fake"}
            p=n.generate("Teste",t,env=env,opener=op)
            self.assertEqual(p,n.generate("Teste",t,env={},opener=op))
            op.assert_called_once()
            p.write_bytes(b"bad")
            with self.assertRaises(n.NarrationError):
                n.generate("Teste",t,env=env,opener=op)
    def test_quota_no_retry(self):
        with tempfile.TemporaryDirectory() as t:
            op=Mock(side_effect=HTTPError(n.URL,429,"quota",None,None))
            env={"FATOVIA_GEMINI_FREE_TIER_VERIFIED":"true","FATOVIA_GEMINI_API_KEY":"fake"}
            with self.assertRaises(n.NarrationError):
                n.generate("Teste",t,env=env,opener=op)
            op.assert_called_once()
    def test_reject_silent_audio(self):
        with self.assertRaises(n.NarrationError):
            n.validate_wav(wav(True))
