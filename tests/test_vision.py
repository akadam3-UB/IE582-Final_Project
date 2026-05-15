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
    color_proxy_detections,
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

    def test_color_proxy_detection_finds_staged_people(self) -> None:
        frame = np.zeros((120, 180, 3), dtype=np.uint8)
        frame[20:86, 14:46] = [0, 0, 220]
        frame[28:92, 66:102] = [25, 180, 25]
        frame[22:84, 126:158] = [210, 45, 25]
        frame[68:112, 92:122] = [35, 210, 230]

        detections = color_proxy_detections(frame, min_area_px=50)
        by_color = {detection.attributes["color"]: detection for detection in detections}

        self.assertEqual(set(by_color), {"red", "green", "blue", "yellow"})
        self.assertEqual(by_color["red"].track_id, 1)
        self.assertEqual(by_color["green"].track_id, 2)
        self.assertEqual(by_color["blue"].track_id, 3)
        self.assertEqual(by_color["yellow"].track_id, 4)
        self.assertLess(by_color["red"].bbox.center_x, by_color["green"].bbox.center_x)
        self.assertGreater(by_color["blue"].bbox.center_x, by_color["green"].bbox.center_x)

    def test_color_proxy_detection_ignores_tiny_noise(self) -> None:
        frame = np.zeros((80, 100, 3), dtype=np.uint8)
        frame[2:5, 2:5] = [0, 0, 255]

        self.assertEqual(color_proxy_detections(frame, min_area_px=50), [])

    def test_color_proxy_detection_prefers_blue_shirt_over_teal_chair(self) -> None:
        frame = np.zeros((120, 180, 3), dtype=np.uint8)
        frame[18:88, 24:54] = [220, 35, 20]
        frame[42:112, 92:162] = [120, 105, 30]

        detections = color_proxy_detections(frame, min_area_px=50)
        blue = next(detection for detection in detections if detection.attributes["color"] == "blue")

        self.assertLess(blue.bbox.center_x, 70)

    def test_top_labels_is_unique_and_ordered(self) -> None:
        detections = [
            Detection("person", 0.9, BoundingBox(0, 0, 10, 10)),
            Detection("cone", 0.8, BoundingBox(0, 0, 10, 10)),
            Detection("person", 0.7, BoundingBox(0, 0, 10, 10)),
        ]

        self.assertEqual(top_labels(detections), ["person", "cone"])


if __name__ == "__main__":
    unittest.main()
