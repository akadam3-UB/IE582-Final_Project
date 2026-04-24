from __future__ import annotations

import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ie582_final_project.models import BoundingBox, CommandIntent, Detection
from ie582_final_project.target_selector import rank_targets, select_target


class TargetSelectorTests(unittest.TestCase):
    def test_prefers_center_with_equal_scores(self) -> None:
        detections = [
            Detection("cone", 0.9, BoundingBox(20, 20, 90, 160), track_id=1),
            Detection("cone", 0.9, BoundingBox(280, 180, 360, 340), track_id=2),
        ]
        intent = CommandIntent(action="track", target_label="cone")
        best = select_target(detections, intent, frame_shape=(480, 640))
        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best.detection.track_id, 2)

    def test_color_match_bonus(self) -> None:
        detections = [
            Detection("cone", 0.85, BoundingBox(260, 180, 340, 340), track_id=3, attributes={"color": "red"}),
            Detection("cone", 0.85, BoundingBox(260, 180, 340, 340), track_id=4, attributes={"color": "yellow"}),
        ]
        intent = CommandIntent(action="track", target_label="cone", target_color="red")
        ranked = rank_targets(detections, intent, frame_shape=(480, 640))
        self.assertEqual(ranked[0].detection.track_id, 3)

    def test_track_id_request_is_strong_preference(self) -> None:
        detections = [
            Detection("person", 0.95, BoundingBox(200, 120, 440, 440), track_id=12),
            Detection("person", 0.95, BoundingBox(220, 120, 430, 430), track_id=7),
        ]
        intent = CommandIntent(action="track", target_label="person", target_track_id=7)
        best = select_target(detections, intent, frame_shape=(480, 640))
        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best.detection.track_id, 7)

    def test_region_hint_prefers_matching_side(self) -> None:
        detections = [
            Detection("person", 0.9, BoundingBox(30, 120, 180, 420), track_id=2),
            Detection("person", 0.9, BoundingBox(420, 120, 590, 420), track_id=9),
        ]
        intent = CommandIntent(action="track", target_label="person", target_region="right")
        best = select_target(detections, intent, frame_shape=(480, 640))
        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best.detection.track_id, 9)

    def test_sticky_track_bonus_reduces_target_switching(self) -> None:
        detections = [
            Detection("person", 0.91, BoundingBox(200, 100, 350, 420), track_id=5),
            Detection("person", 0.93, BoundingBox(250, 100, 420, 430), track_id=11),
        ]
        intent = CommandIntent(action="track", target_label="person")
        best = select_target(detections, intent, frame_shape=(480, 640), sticky_track_id=5)
        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best.detection.track_id, 5)


if __name__ == "__main__":
    unittest.main()
