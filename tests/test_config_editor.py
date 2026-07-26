"""Tests for src/config_editor.py — no network, no Telegram involved.

Each test works against a throwaway copy of the real config/config.yaml so
assertions reflect the actual file shape (comments, indentation, commented-
out entries) rather than a synthetic fixture.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

import config_editor as ce  # noqa: E402

REAL_CONFIG = Path(__file__).resolve().parent.parent / "config" / "config.yaml"


class ConfigEditorTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.tmp_dir) / "config.yaml"
        shutil.copy(REAL_CONFIG, self.config_path)
        self.original_text = self.config_path.read_text(encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def assertFileUnchanged(self):
        self.assertEqual(self.config_path.read_text(encoding="utf-8"), self.original_text)


class BoughtPositionsTests(ConfigEditorTestCase):
    def test_add_new_lot(self):
        ce.add_bought_position("TEST1", "TEST", 12.34, 100, config_path=self.config_path)
        text = self.config_path.read_text(encoding="utf-8")
        self.assertIn('  - id: "TEST1"\n    symbol: TEST\n    entry_price: 12.34\n    shares: 100\n', text)
        # everything before the insertion point is untouched
        self.assertIn('  - id: "EXA"\n    symbol: EXA\n    entry_price: 97.9\n    shares: 6\n', text)

    def test_add_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            ce.add_bought_position("EXA", "EXA", 1.0, 1, config_path=self.config_path)
        self.assertFileUnchanged()

    def test_remove_existing_lot(self):
        ce.remove_bought_position("LPK", config_path=self.config_path)
        text = self.config_path.read_text(encoding="utf-8")
        self.assertNotIn('id: "LPK"', text)
        # neighboring entries survive
        self.assertIn('id: "EXA"', text)
        self.assertIn('id: "SIVE"', text)

    def test_remove_missing_lot_rejected(self):
        with self.assertRaises(ValueError):
            ce.remove_bought_position("DOES_NOT_EXIST", config_path=self.config_path)
        self.assertFileUnchanged()

    def test_add_then_remove_roundtrip_restores_original(self):
        ce.add_bought_position("TEMP", "TEMP", 1.0, 1, config_path=self.config_path)
        ce.remove_bought_position("TEMP", config_path=self.config_path)
        self.assertFileUnchanged()


class WatchlistTests(ConfigEditorTestCase):
    def test_add_new_symbol(self):
        ce.add_watch_symbol("NVDA", config_path=self.config_path)
        text = self.config_path.read_text(encoding="utf-8")
        self.assertIn("  - NVDA\n", text)
        # inserted before the bought_positions section comment, not after it
        self.assertLess(text.index("- NVDA"), text.index("bought_positions:"))

    def test_add_duplicate_symbol_rejected(self):
        with self.assertRaises(ValueError):
            ce.add_watch_symbol("PLTR", config_path=self.config_path)
        self.assertFileUnchanged()

    def test_remove_existing_symbol(self):
        ce.remove_watch_symbol("MU", config_path=self.config_path)
        text = self.config_path.read_text(encoding="utf-8")
        self.assertNotIn("- MU\n", text)
        self.assertIn("- MELI\n", text)

    def test_remove_symbol_with_inline_comment(self):
        ce.remove_watch_symbol("005380.KS", config_path=self.config_path)
        text = self.config_path.read_text(encoding="utf-8")
        self.assertNotIn("005380.KS", text)
        self.assertIn("000660.KS", text)
        self.assertIn("005930.KS", text)

    def test_remove_missing_symbol_rejected(self):
        with self.assertRaises(ValueError):
            ce.remove_watch_symbol("NOPE", config_path=self.config_path)
        self.assertFileUnchanged()

    def test_commented_out_entry_is_not_a_real_symbol(self):
        # "#- HSPS" is commented out in the fixture; it must not block re-adding HSPS
        ce.add_watch_symbol("HSPS", config_path=self.config_path)
        text = self.config_path.read_text(encoding="utf-8")
        self.assertIn("  - HSPS\n", text)


class NotificationSettingsTests(ConfigEditorTestCase):
    def test_set_status_frequency(self):
        ce.set_status_frequency("weekly", config_path=self.config_path)
        text = self.config_path.read_text(encoding="utf-8")
        self.assertIn('status_frequency: "weekly"', text)

    def test_set_status_frequency_invalid_rejected(self):
        with self.assertRaises(ValueError):
            ce.set_status_frequency("hourly", config_path=self.config_path)
        self.assertFileUnchanged()

    def test_set_alert_mode(self):
        ce.set_alert_mode("only_exit", config_path=self.config_path)
        text = self.config_path.read_text(encoding="utf-8")
        self.assertIn('mode: "only_exit"', text)

    def test_set_alert_mode_invalid_rejected(self):
        with self.assertRaises(ValueError):
            ce.set_alert_mode("bogus", config_path=self.config_path)
        self.assertFileUnchanged()

    def test_setting_one_field_does_not_touch_the_other(self):
        ce.set_status_frequency("disabled", config_path=self.config_path)
        text = self.config_path.read_text(encoding="utf-8")
        self.assertIn('mode: "all"', text)  # unchanged default from fixture


if __name__ == "__main__":
    unittest.main()
