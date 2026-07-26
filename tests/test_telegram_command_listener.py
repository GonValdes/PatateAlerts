"""Tests for src/telegram_command_listener.py.

No real Telegram API calls anywhere: HTTP is mocked via unittest.mock, and
config edits go through config_editor bound to a throwaway temp copy of
config.yaml. Safe to run offline / in CI with no credentials.
"""
import functools
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

import config_editor as ce  # noqa: E402
import telegram_command_listener as tcl  # noqa: E402
from storage.db import Database  # noqa: E402

REAL_CONFIG = Path(__file__).resolve().parent.parent / "config" / "config.yaml"

CE_FUNCTIONS = (
    "add_bought_position",
    "remove_bought_position",
    "add_watch_symbol",
    "remove_watch_symbol",
    "set_status_frequency",
    "set_alert_mode",
)


class ListenerTestCase(unittest.TestCase):
    """Binds tcl.ce.* to a temp config copy so handlers never touch the real file."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.tmp_dir) / "config.yaml"
        shutil.copy(REAL_CONFIG, self.config_path)

        self._patches = []
        for name in CE_FUNCTIONS:
            original = getattr(ce, name)
            bound = functools.partial(original, config_path=self.config_path)
            patcher = mock.patch.object(tcl.ce, name, bound)
            patcher.start()
            self._patches.append(patcher)

    def tearDown(self):
        for patcher in self._patches:
            patcher.stop()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def config_text(self) -> str:
        return self.config_path.read_text(encoding="utf-8")


class ParseKwargsTests(unittest.TestCase):
    def test_all_required_present(self):
        parsed = tcl._parse_kwargs(
            ["id=X", "symbol=Y", "entry_price=1.0", "shares=2"],
            ("id", "symbol", "entry_price", "shares"),
        )
        self.assertEqual(parsed, {"id": "X", "symbol": "Y", "entry_price": "1.0", "shares": "2"})

    def test_missing_required_reported(self):
        with self.assertRaisesRegex(ValueError, "symbol, shares"):
            tcl._parse_kwargs(["id=X", "entry_price=1.0"], ("id", "symbol", "entry_price", "shares"))

    def test_unknown_key_reported(self):
        with self.assertRaisesRegex(ValueError, "typo=1"):
            tcl._parse_kwargs(["id=X", "typo=1"], ("id",))

    def test_bare_token_without_equals_is_unrecognized(self):
        with self.assertRaises(ValueError):
            tcl._parse_kwargs(["IREN2"], ("id",))


class HandlerTests(ListenerTestCase):
    def test_add_position_success(self):
        reply = tcl._handle_add_position(["id=TESTX", "symbol=TEST", "entry_price=10.5", "shares=5"])
        self.assertIn("TESTX", reply)
        self.assertIn("✅", reply)
        self.assertIn('id: "TESTX"', self.config_text())

    def test_add_position_missing_field(self):
        with self.assertRaises(ValueError):
            tcl._handle_add_position(["id=TESTX", "symbol=TEST"])
        self.assertNotIn("TESTX", self.config_text())

    def test_add_position_bad_price(self):
        with self.assertRaisesRegex(ValueError, "entry_price"):
            tcl._handle_add_position(["id=TESTX", "symbol=TEST", "entry_price=abc", "shares=5"])

    def test_add_position_bad_shares(self):
        with self.assertRaisesRegex(ValueError, "shares"):
            tcl._handle_add_position(["id=TESTX", "symbol=TEST", "entry_price=1.0", "shares=abc"])

    def test_add_position_duplicate_id(self):
        with self.assertRaisesRegex(ValueError, "already exists"):
            tcl._handle_add_position(["id=EXA", "symbol=EXA", "entry_price=1.0", "shares=1"])

    def test_remove_position_success(self):
        reply = tcl._handle_remove_position(["id=LPK"])
        self.assertIn("✅", reply)
        self.assertNotIn('id: "LPK"', self.config_text())

    def test_remove_position_not_found(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            tcl._handle_remove_position(["id=NOPE"])

    def test_add_watch_success(self):
        reply = tcl._handle_add_watch(["NVDA"])
        self.assertIn("✅", reply)
        self.assertIn("  - NVDA\n", self.config_text())

    def test_add_watch_wrong_arity(self):
        with self.assertRaisesRegex(ValueError, "Usage"):
            tcl._handle_add_watch(["NVDA", "extra"])
        with self.assertRaisesRegex(ValueError, "Usage"):
            tcl._handle_add_watch([])

    def test_remove_watch_success(self):
        reply = tcl._handle_remove_watch(["MU"])
        self.assertIn("✅", reply)
        self.assertNotIn("- MU\n", self.config_text())

    def test_remove_watch_not_found(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            tcl._handle_remove_watch(["NOPE"])

    def test_status_frequency_success(self):
        reply = tcl._handle_status_frequency(["weekly"])
        self.assertIn("✅", reply)
        self.assertIn('status_frequency: "weekly"', self.config_text())

    def test_status_frequency_invalid(self):
        with self.assertRaises(ValueError):
            tcl._handle_status_frequency(["hourly"])

    def test_mode_success(self):
        reply = tcl._handle_mode(["only_exit"])
        self.assertIn("✅", reply)
        self.assertIn('mode: "only_exit"', self.config_text())

    def test_mode_invalid(self):
        with self.assertRaises(ValueError):
            tcl._handle_mode(["bogus"])

    def test_help_lists_all_commands(self):
        reply = tcl._handle_help([])
        for cmd in ("add_position", "remove_position", "add_watch", "remove_watch", "status_frequency", "mode"):
            self.assertIn(f"/{cmd}", reply)


class ProcessMessageTests(ListenerTestCase):
    def setUp(self):
        super().setUp()
        self.sent = []
        self.send_patcher = mock.patch.object(
            tcl, "_send", side_effect=lambda token, chat_id, text: self.sent.append(text)
        )
        self.send_patcher.start()
        self.addCleanup(self.send_patcher.stop)

    def test_recognized_command_sends_ack_then_result(self):
        tcl._process_message("TOK", "CHAT", "/add_watch NVDA")
        self.assertEqual(len(self.sent), 2)
        self.assertEqual(self.sent[0], "📩 Received: /add_watch NVDA")
        self.assertIn("✅", self.sent[1])
        self.assertIn("  - NVDA\n", self.config_text())

    def test_failing_command_sends_ack_then_error(self):
        tcl._process_message("TOK", "CHAT", "/add_watch PLTR")  # already in fixture
        self.assertEqual(len(self.sent), 2)
        self.assertIn("📩 Received", self.sent[0])
        self.assertTrue(self.sent[1].startswith("❌"))

    def test_unknown_command_sends_ack_then_unknown_reply(self):
        tcl._process_message("TOK", "CHAT", "/frobnicate")
        self.assertEqual(len(self.sent), 2)
        self.assertIn("❓", self.sent[1])

    def test_non_command_text_is_ignored(self):
        tcl._process_message("TOK", "CHAT", "just chatting, not a command")
        self.assertEqual(self.sent, [])

    def test_command_with_bot_username_suffix_is_parsed(self):
        tcl._process_message("TOK", "CHAT", "/add_watch@MyBot NVDA")
        self.assertEqual(len(self.sent), 2)
        self.assertIn("✅", self.sent[1])


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class NetworkAndOffsetTests(unittest.TestCase):
    """Exercises _fetch_updates/_send/main with requests fully mocked — no network."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.tmp_dir) / "config.yaml"
        shutil.copy(REAL_CONFIG, self.config_path)
        self.db_path = str(Path(self.tmp_dir) / "test.db")

        self._patches = []
        for name in CE_FUNCTIONS:
            original = getattr(ce, name)
            bound = functools.partial(original, config_path=self.config_path)
            patcher = mock.patch.object(tcl.ce, name, bound)
            patcher.start()
            self._patches.append(patcher)

        db_patcher = mock.patch.object(tcl, "Database", lambda: Database(db_path=self.db_path))
        db_patcher.start()
        self._patches.append(db_patcher)

        # main() calls setup_logging(), which would otherwise write to the real
        # project's logs/ directory; keep tests isolated from it.
        logging_patcher = mock.patch.object(tcl, "setup_logging", lambda: None)
        logging_patcher.start()
        self._patches.append(logging_patcher)

    def tearDown(self):
        for patcher in self._patches:
            patcher.stop()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def config_text(self) -> str:
        return self.config_path.read_text(encoding="utf-8")

    def test_fetch_updates_parses_ok_response(self):
        fake_get = mock.Mock(return_value=FakeResponse({"ok": True, "result": [{"update_id": 5}]}))
        with mock.patch.object(tcl.requests, "get", fake_get):
            updates = tcl._fetch_updates("TOKEN", 3)
        self.assertEqual(updates, [{"update_id": 5}])
        _, kwargs = fake_get.call_args
        self.assertEqual(kwargs["params"]["offset"], 3)

    def test_fetch_updates_handles_api_error(self):
        fake_get = mock.Mock(return_value=FakeResponse({"ok": False, "description": "boom"}))
        with mock.patch.object(tcl.requests, "get", fake_get):
            updates = tcl._fetch_updates("TOKEN", 0)
        self.assertEqual(updates, [])

    def test_offset_roundtrip(self):
        db = Database(db_path=self.db_path)
        self.assertEqual(tcl._get_offset(db), 0)
        tcl._set_offset(db, 42)
        self.assertEqual(tcl._get_offset(db), 42)

    def test_main_processes_authorized_command_and_advances_offset(self):
        env = {"TELEGRAM_BOT_TOKEN": "TOKEN", "TELEGRAM_CHAT_ID": "111"}
        update = {
            "update_id": 100,
            "message": {"chat": {"id": 111}, "text": "/add_watch NVDA"},
        }
        fake_get = mock.Mock(return_value=FakeResponse({"ok": True, "result": [update]}))
        fake_post = mock.Mock(return_value=FakeResponse({"ok": True}))

        with mock.patch.dict(os.environ, env, clear=False), \
                mock.patch.object(tcl.requests, "get", fake_get), \
                mock.patch.object(tcl.requests, "post", fake_post):
            tcl.main()

        self.assertIn("  - NVDA\n", self.config_text())
        self.assertEqual(fake_post.call_count, 2)  # ack + result

        db = Database(db_path=self.db_path)
        self.assertEqual(tcl._get_offset(db), 101)

    def test_main_ignores_unauthorized_chat_but_advances_offset(self):
        env = {"TELEGRAM_BOT_TOKEN": "TOKEN", "TELEGRAM_CHAT_ID": "111"}
        update = {
            "update_id": 200,
            "message": {"chat": {"id": 999}, "text": "/add_watch NVDA"},
        }
        fake_get = mock.Mock(return_value=FakeResponse({"ok": True, "result": [update]}))
        fake_post = mock.Mock(return_value=FakeResponse({"ok": True}))

        with mock.patch.dict(os.environ, env, clear=False), \
                mock.patch.object(tcl.requests, "get", fake_get), \
                mock.patch.object(tcl.requests, "post", fake_post):
            tcl.main()

        self.assertNotIn("  - NVDA\n", self.config_text())
        fake_post.assert_not_called()

        db = Database(db_path=self.db_path)
        self.assertEqual(tcl._get_offset(db), 201)

    def test_main_without_credentials_skips_fetch(self):
        env = {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}
        fake_get = mock.Mock()
        with mock.patch.dict(os.environ, env, clear=False), mock.patch.object(tcl.requests, "get", fake_get):
            tcl.main()
        fake_get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
