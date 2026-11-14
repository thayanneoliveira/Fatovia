import unittest

from scripts.meta_token_lifecycle import WINDOW, remaining_days, should_renew


class TokenLifecycleTests(unittest.TestCase):
    def test_renewal_boundary(self):
        now = 1799854640
        self.assertFalse(should_renew(now + WINDOW + 1, now))
        self.assertTrue(should_renew(now + WINDOW, now))
        self.assertTrue(should_renew(now + 1, now))
        self.assertFalse(should_renew(now, now))
        self.assertFalse(should_renew(now - 1, now))

    def test_remaining_days(self):
        self.assertEqual(remaining_days(86400 * 15, 0), 15)
        self.assertEqual(remaining_days(0, 86400), -1)
