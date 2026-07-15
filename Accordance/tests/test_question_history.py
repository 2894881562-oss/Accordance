import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from core.question_history import (
    HISTORY_SCHEMA_VERSION,
    QuestionHistory,
    _compact_entry,
    build_duplicate_decision,
    record_question,
)


class QuestionHistoryTests(unittest.TestCase):
    def test_context_does_not_dilute_duplicate_matching(self):
        history = QuestionHistory(history_file="unused-history.json", disabled=False)
        history._loaded = True
        with patch.object(history, "_save", return_value=True):
            self.assertTrue(
                history.add_question(
                    "same question",
                    "test",
                    "result",
                    context="omen: bird",
                )
            )
        duplicate = build_duplicate_decision("same question", "test", history)
        self.assertTrue(duplicate["is_duplicate"])
        self.assertEqual(duplicate["similarity"], 1.0)
        self.assertEqual(duplicate["matched"]["context"], "omen: bird")

    def test_legacy_entry_migrates_without_empty_context(self):
        compacted = _compact_entry({
            "v": 2,
            "q": "question",
            "m": "module",
            "t": 1,
            "dt": "1970-01-01 00:00:01",
            "r": "result",
        })
        self.assertEqual(compacted["v"], HISTORY_SCHEMA_VERSION)
        self.assertNotIn("c", compacted)

    def test_disabled_history_returns_false_and_explains(self):
        disabled = Mock()
        disabled.add_question.return_value = False
        disabled._disabled = True
        with patch("core.question_history._session_history", disabled):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertFalse(record_question("q", "m", "r"))
        self.assertIn("ACCORDANCE_HISTORY_DISABLED", output.getvalue())

    def test_failed_save_rolls_back_in_memory_addition(self):
        history = QuestionHistory(history_file="unused-history.json", disabled=False)
        history._loaded = True
        original = _compact_entry({
            "question": "old question",
            "module": "test",
            "timestamp": 1,
            "datetime": "1970-01-01 00:00:01",
            "result_summary": "old result",
        })
        history._history = [original]

        with patch.object(history, "_save", return_value=False):
            self.assertFalse(history.add_question("new question", "test", "new result"))

        self.assertEqual(history._history, [original])

    def test_failed_clear_restores_in_memory_history(self):
        history = QuestionHistory(history_file="unused-history.json", disabled=False)
        history._loaded = True
        original = _compact_entry({
            "question": "keep question",
            "module": "test",
            "timestamp": 1,
            "datetime": "1970-01-01 00:00:01",
            "result_summary": "keep result",
        })
        history._history = [original]

        with patch.object(history, "_save", return_value=False):
            self.assertFalse(history.clear())

        self.assertEqual(history._history, [original])


if __name__ == "__main__":
    unittest.main()
