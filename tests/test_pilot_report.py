import unittest
from datetime import datetime
from fatovia.pilot_report import build

P={"pilot_id":"test","start_date":"2026-11-15","end_date":"2026-11-21","max_total":4,"max_daily":2,
"items":[{"id":"camara:1","version":"v"}]}
POST={"id":"camara:1","version":"v","media_id":"123456","published_at":"2026-11-15T09:12:00-03:00"}
def now(s): return datetime.fromisoformat(s)
def sample(h):
    return {"media_id":"123456","target_hours":h,"age_hours":h+0.5,"reach":10,"saved":0,"shares":0}
class PilotReportTests(unittest.TestCase):
    def test_before_start(self):
        r=build({},P,now("2026-11-14T17:00:00-03:00"))
        self.assertEqual(r["status"],"awaiting_start")
        self.assertFalse(r["next_phase_authorized"])
    def test_no_missing_as_zero(self):
        r=build({"published":[POST]},P,now("2026-11-19T09:00:00-03:00"))
        self.assertEqual(r["publications"][0]["samples"]["24"]["status"],"window_missed")
        self.assertFalse(r["evaluation_ready"])
    def test_both_samples_and_no_promotion(self):
        r=build({"published":[POST],"metric_cohorts":[sample(24),sample(72)]},P,now("2026-11-22T09:00:00-03:00"))
        self.assertEqual(r["samples_collected"],{"24":1,"72":1})
        self.assertTrue(r["evaluation_ready"])
        self.assertFalse(r["next_phase_authorized"])
    def test_transaction(self):
        r=build({"publishing":{"status":"uncertain"}},P,now("2026-11-16T09:00:00-03:00"))
        self.assertEqual(r["status"],"transaction_requires_attention")
    def test_other_media_excluded(self):
        r=build({"published":[POST],"metric_cohorts":[{**sample(24),"media_id":"777777"}]},P,now("2026-11-16T10:00:00-03:00"))
        self.assertEqual(r["samples_collected"]["24"],0)
    def test_outside_policy_is_not_success(self):
        r=build({"published":[{**POST,"id":"camara:99"}]},P,now("2026-11-16T10:00:00-03:00"))
        self.assertEqual(r["status"],"review_required")
