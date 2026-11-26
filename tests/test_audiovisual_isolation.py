"""Integration regression: a rejected Reel does not block an eligible carousel.
Mocks only eligibility, not media delivery. Existing publisher remains the sole writer.
"""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch
from fatovia import publisher

class IndependentFormatQueueTests(unittest.TestCase):
    def test_reel_rejection_isolated_from_carousel(self):
        now=datetime(2026,11,26,17,10,tzinfo=ZoneInfo("America/Sao_Paulo"))
        good={"id":"camara:2655462","version":"12345678901234","format":"carousel","editorial_score":9}
        bad={"id":"reel:rejected","version":"12345678901234","format":"reel","editorial_score":99}
        state={"pending":[good],"reel_pending":[bad],"published":[],"publishing":None}
        cfg={"enabled":True,"token":"dummy","ig_id":"123456789"}
        with patch.object(publisher.mf,"allowed",side_effect=lambda s,p,t: p["format"]=="carousel"),\
             patch.object(publisher,"isolate_rejected",return_value=[]),\
             patch.object(publisher,"load",return_value={"reviews":[]}),\
             patch.object(publisher,"qualified",return_value=True),\
             patch.object(publisher,"approved",return_value=True),\
             patch.object(publisher,"save"):
            result=publisher.prepare(state,now,cfg)
        self.assertEqual(result["action"],"prepared")
        self.assertEqual(result["id"],good["id"])
        self.assertEqual(result["format"],"carousel")
        self.assertEqual(len(state["reel_pending"]),1)
        self.assertEqual(state["publishing"]["id"],good["id"])
    def test_no_new_publisher_in_factory(self):
        from fatovia import audiovisual_factory
        from pathlib import Path
        src=Path(audiovisual_factory.__file__).read_text()
        self.assertNotIn("media_publish",src)
        self.assertNotIn("META_ACCESS_TOKEN",src)

if __name__=="__main__":unittest.main()
