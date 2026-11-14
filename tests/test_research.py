import unittest
import json
from datetime import datetime
from fatovia.research import parse,collect

NOW=datetime.fromisoformat("2026-11-14T17:00:00-03:00")
def body(*rows):
    return json.dumps([{"data":d,"valor":v} for d,v in rows]).encode()

class ResearchTests(unittest.TestCase):
    def test_sort_and_units(self):
        rows,status=parse(body(("13/11/2026","10.50"),("12/11/2026","10.50")),"432",NOW)
        self.assertEqual(status,"ok")
        self.assertEqual(rows[0]["source_date"],"2026-11-12")
        self.assertEqual(rows[-1]["value"],"10.50")
    def test_future_and_duplicate(self):
        with self.assertRaises(ValueError):
            parse(body(("15/11/2026","10")),"432",NOW)
        with self.assertRaises(ValueError):
            parse(body(("01/10/2026","0.5"),("02/10/2026","0.6")),"16122",NOW)
    def test_stale(self):
        _,status=parse(body(("01/01/2026","10")),"432",NOW)
        self.assertEqual(status,"stale")
    def test_no_invented_data(self):
        def fail(*args): raise TimeoutError()
        report=collect(NOW,fail)
        for row in report["series"].values():
            self.assertEqual(row["status"],"unavailable")
            self.assertNotIn("observations",row)
            self.assertFalse(row["publication_authorized"])
    def test_context_never_approves(self):
        report=collect(NOW,lambda *args:body(("13/11/2026","1.25")))
        self.assertFalse(report["publication_authorized"])
