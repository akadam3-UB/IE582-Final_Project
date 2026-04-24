from __future__ import annotations

import pathlib
import sys
import unittest
from types import SimpleNamespace

import numpy as np

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ie582_final_project.models import BoundingBox, Detection
from ie582_final_project.vision import (
    build_scene_summary,
    estimate_detection_attributes,
    top_labels,
    ultralytics_results_to_detections,
)


class VisionUtilsTests(unittest.TestCase):
    def test_build_scene_summary_mentions_key_attributes(self) -> None:
        detections = [
            Detection(
                label="person",
                confidence=0.95,
                track_id=7,
                bbox=BoundingBox(50, 80, 180, 300),
                attributes={"color": "red"},
            ),
            Detection(
                label="cone",
                confidence=0.85,
                track_id=3,
                bbox=BoundingBox(280, 120, 340, 260),
            ),
        ]

        summary = build_scene_summary(detections)
        self.assertIn("person id=7", summary)
        self.assertIn("color=red", summary)
        self.assertIn("cone id=3", summary)

    def test_estimate_detection_attributes_detects_red_region(self) -> None:
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        frame[20:100, 40:120] = [0, 0, 255]

        attrs = estimate_detection_attributes(frame, BoundingBox(30, 10, 130, 110))
        self.assertEqual(attrs.get("color"), "red")

    def test_ultralytics_conversion_keeps_detection_without_track_id(self) -> None:
        boxes = SimpleNamespace(
            id=None,
            cls=np.array([0]),
            conf=np.array([0.8]),
            xyxy=np.array([[10.0, 20.0, 30.0, 60.0]]),
        )
        results = [SimpleNamespace(boxes=boxes, names={0: "person"})]

        detections = ultralytics_results_to_detections(results)
        self.assertEqual(len(detections), 1)
        self.assertIsNone(detections[0].track_id)
        self.assertEqual(detections[0].label, "person")

    def test_top_labels_is_unique_and_ordered(self) -> None:
        detections = [
            Detection("person", 0.9, BoundingBox(0, 0, 10, 10)),
            Detection("cone", 0.8, BoundingBox(0, 0, 10, 10)),
            Detection("person", 0.7, BoundingBox(0, 0, 10, 10)),
        ]

        self.assertEqual(top_labels(detections), ["person", "cone"])


if __name__ == "__main__":
    unittest.main()
