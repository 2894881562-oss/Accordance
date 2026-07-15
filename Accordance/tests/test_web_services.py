import datetime
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from core.bazi import parse_birth_datetime
from web.schemas import DivinationRequest, MethodSelectorRequest
from web.services import _gate_duplicate, run_divination


class WebServiceTests(unittest.TestCase):
    def test_full_and_quick_keep_question_and_context_separate(self):
        checks = []
        records = []

        def fake_check(client_id, question, module_label, match_mode="semantic"):
            checks.append((question, module_label, match_mode))
            return {"is_duplicate": False, "action": "none"}

        def fake_record(client_id, question, module_label, summary, context=""):
            records.append((question, module_label, context))
            return True

        with patch("web.services.check_duplicate", side_effect=fake_check), patch(
            "web.services.record_question", side_effect=fake_record
        ):
            run_divination("full", DivinationRequest(
                question="same question",
                external_omen="bird sound",
                focus_seed=321,
            ), "client")
            run_divination("quick", DivinationRequest(
                question="same question",
                external_omen="door sound",
                focus_seed=654,
            ), "client")

        self.assertEqual([item[0] for item in checks], ["same question", "same question"])
        self.assertEqual([item[0] for item in records], ["same question", "same question"])
        self.assertTrue(records[0][2].endswith("bird sound"))
        self.assertTrue(records[1][2].endswith("door sound"))

    def test_force_state_is_not_inferred_from_history_write(self):
        duplicate = {"is_duplicate": True, "action": "warn"}
        with patch("web.services.check_duplicate", return_value=duplicate):
            blocked = _gate_duplicate("client", "q", "m", False)
            forced = _gate_duplicate("client", "q", "m", True)
        self.assertTrue(blocked["confirmation_required"])
        self.assertFalse(forced["confirmation_required"])

    def test_invalid_business_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            run_divination("decision", DivinationRequest(
                question="choose",
                option_a="same",
                option_b="SAME",
                focus_seed=1,
            ), "client")
        with self.assertRaises(ValueError):
            run_divination("item", DivinationRequest(
                item_name="keys",
                search_scope="9",
                focus_seed=1,
            ), "client")
        with self.assertRaises(ValueError):
            run_divination("full", DivinationRequest(question="q"), "client")

    def test_method_selector_rejects_blank_and_trims_question(self):
        with self.assertRaises(ValidationError):
            MethodSelectorRequest.model_validate({"question": "   "})
        payload = MethodSelectorRequest.model_validate({"question": "  是否出行  "})
        self.assertEqual(payload.question, "是否出行")

    def test_birth_date_rejects_unsupported_or_future_date(self):
        with self.assertRaisesRegex(ValueError, "公元 2 年"):
            parse_birth_datetime("0001-01-01", 0)
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        with self.assertRaisesRegex(ValueError, "不能晚于今天"):
            parse_birth_datetime(tomorrow.isoformat(), 0)


if __name__ == "__main__":
    unittest.main()
