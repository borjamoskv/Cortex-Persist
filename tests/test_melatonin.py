"""Tests for DigitalEndocrine melatonin expansion."""

import unittest

from cortex.sovereign.endocrine import DigitalEndocrine


class TestMelatoninExpansion(unittest.TestCase):
    def test_melatonin_initialized_to_zero(self):
        endo = DigitalEndocrine()
        self.assertEqual(endo.melatonin, 0.0)

    def test_sleep_context_raises_melatonin(self):
        endo = DigitalEndocrine()
        endo.ingest_context("necesito dormir, mucha fatiga")
        self.assertGreater(endo.melatonin, 0.0)

    def test_sync_circadian_sleep_raises_melatonin(self):
        endo = DigitalEndocrine()
        for _ in range(10):
            endo.sync_circadian(is_sleeping=True)
        self.assertGreater(endo.melatonin, 0.3)
        # Cortisol should decay during sleep
        self.assertLessEqual(endo.cortisol, 0.0)

    def test_sync_circadian_wake_lowers_melatonin(self):
        endo = DigitalEndocrine()
        # Spike melatonin via sleep
        for _ in range(10):
            endo.sync_circadian(is_sleeping=True)
        high = endo.melatonin
        # Wake up
        for _ in range(10):
            endo.sync_circadian(is_sleeping=False)
        self.assertLess(endo.melatonin, high)

    def test_high_melatonin_lowers_temperature(self):
        endo = DigitalEndocrine()
        temp_before = endo.temperature
        for _ in range(20):
            endo.sync_circadian(is_sleeping=True)
        temp_after = endo.temperature
        self.assertLess(temp_after, temp_before)

    def test_high_melatonin_sets_drowsy_style(self):
        endo = DigitalEndocrine()
        for _ in range(20):
            endo.sync_circadian(is_sleeping=True)
        self.assertEqual(endo.response_style, "drowsy")

    def test_melatonin_in_to_dict(self):
        endo = DigitalEndocrine()
        data = endo.to_dict()
        self.assertIn("melatonin", data["hormones"])
        self.assertEqual(data["hormones"]["melatonin"], 0.0)

    def test_homeostasis_decays_melatonin(self):
        endo = DigitalEndocrine()
        endo.melatonin = 0.5
        endo._homeostasis()
        self.assertLess(endo.melatonin, 0.5)


if __name__ == "__main__":
    unittest.main()
