from __future__ import annotations

import unittest
from pathlib import Path


class SkillContractTests(unittest.TestCase):
    def test_skill_explains_parse_then_read_when_no_markdown_path_exists(self):
        skill = (Path(__file__).parents[1] / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("no previous parse result", skill)
        self.assertIn("first call `parse_document`", skill)
        self.assertIn("MHTML/MHT", skill)
        self.assertIn("structured_content_path", skill)
        self.assertIn("`tier`", skill)


if __name__ == "__main__":
    unittest.main()
