import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from core.cli_input import ask_choice, ask_text, present_conclusion
from modules.decision_helper import _ask_option
from modules.multi_decision import _ask_options, parse_multi_options_text
from modules.name_divination import _input_positive_int


class CliInputTests(unittest.TestCase):
    def test_required_text_reprompts_for_blank_and_overflow(self):
        with patch("builtins.input", side_effect=["", "toolong", " ok "]):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(ask_text("prompt", "field", 3), "ok")

    def test_choice_uses_default_and_rejects_invalid_value(self):
        with patch("builtins.input", return_value=""):
            self.assertEqual(ask_choice("prompt", "choice", ("1", "2"), default="1"), "1")
        with patch("builtins.input", side_effect=["3", "2"]):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(ask_choice("prompt", "choice", ("1", "2")), "2")

    def test_conclusion_is_collapsed_by_default(self):
        with patch("builtins.input", return_value=""):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertFalse(present_conclusion("summary"))
        self.assertIn("summary", output.getvalue())

    def test_option_duplicates_are_case_insensitive(self):
        with patch("builtins.input", side_effect=["PLAN", "other"]):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(_ask_option("B", existing={"plan"}), "other")
        with patch("builtins.input", side_effect=["Plan", "plan", "Growth", "Hold"]):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(_ask_options(3), ["Plan", "Growth", "Hold"])
        with self.assertRaises(ValueError):
            parse_multi_options_text("Plan\nplan\nHold")

    def test_manual_name_stroke_is_bounded(self):
        with patch("builtins.input", side_effect=["1000", "999"]):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(_input_positive_int("prompt"), 999)


if __name__ == "__main__":
    unittest.main()
