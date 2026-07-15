import unittest

from core.rule_audit import run_rule_audit


class RuleAuditTests(unittest.TestCase):
    def test_complete_rule_audit_has_no_errors_or_warnings(self):
        result = run_rule_audit()
        self.assertTrue(result["passed"], result["issues"])
        self.assertEqual(result["warning_count"], 0, result["issues"])


if __name__ == "__main__":
    unittest.main()
