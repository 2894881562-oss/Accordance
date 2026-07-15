import unittest

from core.interpretation import _build_category_conclusion


class InterpretationTests(unittest.TestCase):
    def test_marriage_with_official_ghost_yongshen_uses_marriage_branch(self):
        strong_line = {"strength_score": 3}

        marriage = _build_category_conclusion(
            "婚恋女占", "官鬼", 2, [strong_line], [], [], "", {}, None
        )
        career = _build_category_conclusion(
            "官职压力", "官鬼", 2, [strong_line], [strong_line], [], "", {}, None
        )

        self.assertIn("感情", marriage)
        self.assertNotIn("事业", marriage)
        self.assertIn("事业", career)


if __name__ == "__main__":
    unittest.main()
