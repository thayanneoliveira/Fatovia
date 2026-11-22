import unittest
from unittest.mock import patch
from tools.recovery_agent import diagnose

class RecoveryAgentTests(unittest.TestCase):
    def test_does_not_publish_or_bypass(self):
        result = diagnose()
        self.assertFalse(result["publish_attempted"])
        self.assertFalse(result["gates_modified"])
        self.assertEqual(result["additional_spend_brl"], 0)
        self.assertTrue(all(not x["safe_auto"] for x in result["findings"]))
    def test_identifies_current_blockers(self):
        codes = {x["code"] for x in diagnose()["findings"]}
        self.assertIn("PILOT_META_RECONCILIATION", codes)
        self.assertIn("PRODUCTION_TRANSITION", codes)
        self.assertIn("APPROVED_QUEUE_EMPTY", codes)

if __name__ == "__main__":
    unittest.main()
