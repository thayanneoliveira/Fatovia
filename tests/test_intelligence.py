import unittest
from datetime import datetime, timezone
from fatovia.discovery import parse_rss, summarize
from fatovia.cohorts import age_bucket, extract, learning_report


class DiscoveryTests(unittest.TestCase):
    def test_recent_and_allowlisted_only(self):
        now=datetime(2026,11,14,16,tzinfo=timezone.utc)
        body=b"""<rss><channel>
        <item><title>Orcamento e renda</title><link>https://agenciabrasil.ebc.com.br/economia/a?trk=1</link><pubDate>Sat, 14 Nov 2026 12:00:00 GMT</pubDate></item>
        <item><title>Renda</title><link>https://example.org/a</link><pubDate>Sat, 14 Nov 2026 12:00:00 GMT</pubDate></item>
        <item><title>Renda</title><link>https://agenciabrasil.ebc.com.br/economia/b</link><pubDate>Sat, 01 Nov 2025 12:00:00 GMT</pubDate></item>
        </channel></rss>"""
        rows=parse_rss(body,"agencia_brasil","agenciabrasil.ebc.com.br",now)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["status"],"discovery_only")
        self.assertEqual(rows[0]["url"],"https://agenciabrasil.ebc.com.br/economia/a")
        self.assertEqual(summarize(rows,{},now)[0]["status"],"research_required")

    def test_reject_xml_entities(self):
        with self.assertRaises(ValueError):
            parse_rss(b'<!DOCTYPE rss [<!ENTITY a "x">]><rss/>',"test","example.org",datetime.now(timezone.utc))


class CohortTests(unittest.TestCase):
    def test_age_windows(self):
        self.assertIsNone(age_bucket(23.99))
        self.assertEqual(age_bucket(24),24)
        self.assertIsNone(age_bucket(31))
        self.assertEqual(age_bucket(72),72)
        self.assertIsNone(age_bucket(79))

    def test_missing_is_not_zero(self):
        self.assertIsNone(extract({"data":[]},"shares"))
        self.assertEqual(extract({"data":[{"name":"shares","values":[{"value":0}]}]},"shares"),0)

    def test_learning_requires_samples(self):
        self.assertEqual(learning_report({})["status"],"insufficient_sample")
