"""Regression coverage for unidentified Unique name inference."""

import ast
from collections import defaultdict
from pathlib import Path
import re
import unittest


def load_unique_definition():
    """Load the pure helper without executing the inventory build script."""
    source_path = Path(__file__).parents[1] / "treasure_vault" / "support" / "polish.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "unique_definition"
    )
    namespace = {
        "unique": {"123": {"index": "Amulet of the Viper", "code": "vip"}},
        "unique_by_code": defaultdict(
            list,
            {"xea": [{"index": "Skin of the Vipermagi", "code": "xea"}]},
        ),
        "base_code_by_name": {"serpentskinarmor": "xea"},
        "normalize": lambda value: re.sub("[^a-z0-9]", "", value.lower()),
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]), source_path, "exec"), namespace)
    return namespace["unique_definition"]


class UniqueDefinitionTests(unittest.TestCase):
    def setUp(self):
        self.definition = load_unique_definition()

    def test_identified_set_does_not_resolve_through_unique_id_table(self):
        item = {
            "quality": 5,
            "identified": 1,
            "unique_set_id": 123,
            "base_name": "Cap",
        }

        self.assertIsNone(self.definition(item))

    def test_identified_unique_is_not_inferred_or_tagged_unidentified(self):
        item = {
            "quality": 7,
            "identified": 1,
            "unique_set_id": 123,
            "base_name": "Amulet",
        }

        self.assertIsNone(self.definition(item))

    def test_unidentified_unique_still_uses_exact_and_base_fallbacks(self):
        exact = self.definition({
            "quality": 7,
            "identified": 0,
            "unique_set_id": 123,
            "base_name": "Amulet",
        })
        fallback = self.definition({
            "quality": 7,
            "identified": 0,
            "unique_set_id": 0,
            "base_name": "Serpentskin Armor",
        })

        self.assertEqual(exact["index"], "Amulet of the Viper")
        self.assertEqual(fallback["index"], "Skin of the Vipermagi")


if __name__ == "__main__":
    unittest.main()
