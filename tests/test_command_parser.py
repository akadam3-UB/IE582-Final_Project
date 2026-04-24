from __future__ import annotations

import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ie582_final_project.command_parser import parse_command, parse_rule_based, parse_vlm_json


class CommandParserTests(unittest.TestCase):
    def test_rule_parser_extracts_action_label_color(self) -> None:
        intent = parse_rule_based("Track the red cone")
        self.assertEqual(intent.action, "track")
        self.assertEqual(intent.target_label, "cone")
        self.assertEqual(intent.target_color, "red")

    def test_rule_parser_extracts_region_and_classroom_synonym(self) -> None:
        intent = parse_rule_based("track the professor on the left")
        self.assertEqual(intent.target_label, "person")
        self.assertEqual(intent.target_region, "left")

    def test_rule_parser_extracts_go_to_and_track_id(self) -> None:
        intent = parse_rule_based("go to track 17 slowly")
        self.assertEqual(intent.action, "go_to")
        self.assertEqual(intent.target_track_id, 17)
        self.assertLess(intent.speed_scale, 1.0)

    def test_vlm_json_with_wrapper_text(self) -> None:
        text = 'Sure, here it is: {"action":"go_to","target_label":"person","speed_scale":0.8}'
        intent = parse_vlm_json(text, raw_text="go to the person")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.action, "go_to")
        self.assertEqual(intent.target_label, "person")
        self.assertAlmostEqual(intent.speed_scale, 0.8)

    def test_parse_command_merges_vlm_fields(self) -> None:
        intent = parse_command(
            "track the cone",
            vlm_text='{"action":"go_to","target_label":"cone","target_region":"right","speed_scale":1.1}',
        )
        self.assertEqual(intent.action, "go_to")
        self.assertEqual(intent.target_label, "cone")
        self.assertEqual(intent.target_region, "right")
        self.assertAlmostEqual(intent.speed_scale, 1.1)


if __name__ == "__main__":
    unittest.main()
