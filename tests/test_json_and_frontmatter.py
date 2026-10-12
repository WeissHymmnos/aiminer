import unittest

from core.frontmatter import dump_frontmatter, parse_frontmatter
from core.json_parser import parse_llm_json, parse_llm_model
from schemas.messages import ImplementationOutput


class TestJsonParser(unittest.TestCase):
    def test_strip_markdown_code_fences(self):
        raw = "```json\n{\"hypothesis_name\": \"Test\", \"hypothesis_description\": \"Desc\", \"rationale\": \"Rat\"}\n```"
        res = parse_llm_json(raw)
        self.assertEqual(res["hypothesis_name"], "Test")

    def test_parse_latex_math_formulas(self):
        raw = '{"math_formula": "\\alpha_t = \\frac{close_t}{open_t}", "variables_defined": {"close_t": "close"}}'
        res = parse_llm_json(raw)
        self.assertIn("close_t", res["math_formula"])

    def test_parse_llm_model(self):
        raw = '{"code_expression": "CSRank($close)", "is_valid_syntax": true}'
        model = parse_llm_model(raw, ImplementationOutput)
        self.assertEqual(model.code_expression, "CSRank($close)")
        self.assertTrue(model.is_valid_syntax)


class TestFrontmatter(unittest.TestCase):
    def test_roundtrip_frontmatter(self):
        meta = {
            "title": "Momentum Reversal",
            "type": "factor_card",
            "tags": ["momentum", "reversal"],
            "ic": 0.05,
            "is_effective": True,
        }
        body = "## Content\nThis is a test body."
        rendered = dump_frontmatter(meta, body)
        parsed_meta, parsed_body = parse_frontmatter(rendered)

        self.assertEqual(parsed_meta["title"], "Momentum Reversal")
        self.assertEqual(parsed_meta["type"], "factor_card")
        self.assertEqual(parsed_meta["tags"], ["momentum", "reversal"])
        self.assertIn("Content", parsed_body)


if __name__ == "__main__":
    unittest.main()
