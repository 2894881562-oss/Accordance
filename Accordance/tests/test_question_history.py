import datetime
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, mock_open, patch

from core.question_history import (
    HISTORY_SCHEMA_VERSION,
    MAX_HISTORY_READ_BYTES,
    QuestionHistory,
    _compact_entry,
    _expand_with_synonyms,
    _question_similarity,
    build_duplicate_decision,
    record_question,
)


class QuestionHistoryTests(unittest.TestCase):
    def test_synonym_normalization_is_single_pass_and_stable(self):
        self.assertEqual(_expand_with_synonyms("赚钱"), "「钱」")
        self.assertEqual(_expand_with_synonyms("赚钱"), _expand_with_synonyms("工资"))
        self.assertEqual(_expand_with_synonyms("赚钱"), _expand_with_synonyms("钱"))

    def test_similarity_calibration_keeps_objects_distinct(self):
        self.assertEqual(_question_similarity("项目如何？", "项目如何"), 1.0)
        self.assertGreaterEqual(
            _question_similarity("该不该换工作", "要不要跳槽"),
            0.78,
        )
        self.assertLess(_question_similarity("钥匙在哪里", "手机在哪里"), 0.62)
        self.assertLess(
            _question_similarity("张三工作发展如何", "李四工作发展如何"),
            0.62,
        )
        self.assertLess(
            _question_similarity("甲公司面试能否通过", "乙公司面试能否通过"),
            0.62,
        )
        self.assertGreaterEqual(
            _question_similarity("张三工作发展如何", "张三事业前景怎样"),
            0.78,
        )
        self.assertGreaterEqual(
            _question_similarity("未来三个月项目如何", "项目未来三个月如何"),
            0.78,
        )

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

    def test_invalid_or_future_timestamp_falls_back_safely(self):
        now = 1_700_000_000.0
        with patch("core.question_history.time.time", return_value=now):
            for invalid in (float("nan"), float("inf"), -1e300, 1e300, now + 301):
                with self.subTest(timestamp=invalid):
                    compacted = _compact_entry({
                        "question": "question",
                        "module": "module",
                        "timestamp": invalid,
                        "result_summary": "result",
                    })
                    self.assertEqual(compacted["t"], now)
                    datetime.datetime.strptime(compacted["dt"], "%Y-%m-%d %H:%M:%S")

    def test_malformed_text_fields_are_compacted_without_crashing(self):
        compacted = _compact_entry({
            "question": ["question", {"nested": True}],
            "module": {"name": "module"},
            "timestamp": 1,
            "result_summary": 123,
            "context": ["x" * 300],
        })

        self.assertEqual(compacted["q"], '["question",{"nested":true}]')
        self.assertEqual(compacted["m"], '{"name":"module"}')
        self.assertEqual(compacted["r"], "123")
        self.assertLessEqual(len(compacted["c"]), 180)

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

    def test_corrupt_history_is_not_overwritten_by_automatic_save(self):
        history = QuestionHistory(history_file="corrupt-history.json", disabled=False)
        with patch("core.question_history.os.path.exists", return_value=True), patch(
            "core.question_history.os.path.getsize", return_value=9
        ), patch(
            "builtins.open", mock_open(read_data="{not-json")
        ):
            self.assertEqual(history.get_recent(), [])

        self.assertFalse(history.stats()["available"])
        with patch.object(history, "_save", wraps=history._save) as save:
            self.assertFalse(history.add_question("new question", "test", "result"))
        save.assert_called_once()
        self.assertEqual(history._history, [])

    def test_oversized_history_is_not_opened(self):
        history = QuestionHistory(history_file="oversized-history.json", disabled=False)
        file_open = mock_open(read_data="[]")
        with patch("core.question_history.os.path.exists", return_value=True), patch(
            "core.question_history.os.path.getsize",
            return_value=MAX_HISTORY_READ_BYTES + 1,
        ), patch("builtins.open", file_open):
            self.assertEqual(history.get_recent(), [])

        file_open.assert_not_called()
        self.assertTrue(history._load_failed)

    def test_explicit_clear_can_recover_failed_load_state(self):
        history = QuestionHistory(history_file="corrupt-history.json", disabled=False)
        history._loaded = True
        history._load_failed = True

        with patch.object(history, "_save", return_value=True):
            self.assertTrue(history.clear())

        self.assertFalse(history._load_failed)


if __name__ == "__main__":
    unittest.main()
