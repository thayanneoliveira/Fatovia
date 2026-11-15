import unittest
from datetime import datetime
from unittest.mock import patch
from fatovia.pilot import allowed,window_slot
NOW=datetime.fromisoformat("2026-11-15T09:12:00-03:00")
ITEM={"id":"camara:1","version":"v","template_revision":"documentary-hook-v3"}
POL={"schema":1,"status":"prepared","start_date":"2026-11-15","end_date":"2026-11-21","max_total":4,"max_daily":2,"allowed_hours":[9,17],"template_revision":"documentary-hook-v3","items":[{"id":"camara:1","version":"v","content_sha256":"test","card_sha256":["x"]*7}]}
class PilotTests(unittest.TestCase):
    def setUp(self):
        for name,value in [("fingerprint","test"),("inspect_files",["x"]*7)]:
            p=patch("fatovia.pilot."+name,return_value=value);p.start();self.addCleanup(p.stop)
    def test_scoped(self):
        self.assertTrue(allowed({"published":[]},ITEM,NOW,POL))
        self.assertFalse(allowed({"published":[]},{**ITEM,"id":"camara:2"},NOW,POL))
        self.assertFalse(allowed({"published":[]},ITEM,NOW,{**POL,"status":"paused"}))
    def test_time(self):
        self.assertFalse(allowed({"published":[]},ITEM,NOW.replace(day=22),POL))
        self.assertFalse(allowed({"published":[]},ITEM,NOW.replace(hour=13),POL))
    def test_caps(self):
        self.assertFalse(allowed({"published":[{"published_at":NOW.isoformat()}]*2},ITEM,NOW,POL))
        self.assertFalse(allowed({"published":[{"published_at":NOW.isoformat()}]*4},ITEM,NOW.replace(day=16),POL))
    def test_content_tampered(self):
        with patch("fatovia.pilot.fingerprint",return_value="changed"):
            self.assertFalse(allowed({"published":[]},ITEM,NOW,POL))

    def test_delayed_start_inside_same_window(self):
        for h,m in [(9,59),(10,24),(10,59),(17,58),(18,59)]:
            self.assertTrue(allowed({"published":[]},ITEM,NOW.replace(hour=h,minute=m),POL))
        for h,m in [(8,59),(11,0),(16,59),(19,0)]:
            self.assertFalse(allowed({"published":[]},ITEM,NOW.replace(hour=h,minute=m),POL))
    def test_no_second_post_in_same_window(self):
        history={"published":[{"published_at":NOW.isoformat()}]}
        self.assertFalse(allowed(history,ITEM,NOW.replace(hour=10,minute=24),POL))
        self.assertTrue(allowed(history,ITEM,NOW.replace(hour=17,minute=24),POL))
    def test_slot_in_brussels_or_utc_is_brt(self):
        self.assertEqual(window_slot(datetime.fromisoformat("2026-11-15T13:59:00+00:00")),9)
