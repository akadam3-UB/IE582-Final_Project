from __future__ import annotations

import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ie582_final_project.models import BoundingBox, Detection
from ie582_final_project.pan_tilt_pipeline import PanTiltTargetingPipeline


class PanTiltPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = PanTiltTargetingPipeline()
        self.joints = {
            "arm_shoulder_pan_joint": {
                "angle_deg": 57.0,
                "min_angle": 0.0,
                "max_angle": 114.0,
            },
            "arm_shoulder_lift_joint": {
                "angle_deg": 125.0,
                "min_angle": 45.0,
                "max_angle": 160.0,
            },
        }

    def test_stop_intent_outputs_empty_command(self) -> None:
        self.pipeline.update_command("stop")
        cmd, best, ranked = self.pipeline.step([], (480, 640), self.joints, robot_id=1)
        self.assertFalse(cmd.has_update)
        self.assertIsNone(best)
        self.assertEqual(ranked, [])

    def test_track_command_selects_requested_label(self) -> None:
        self.pipeline.update_command("track the red cone")
        detections = [
            Detection("person", 0.95, BoundingBox(90, 100, 240, 420), track_id=1, attributes={"color": "blue"}),
            Detection("cone", 0.88, BoundingBox(350, 180, 430, 350), track_id=2, attributes={"color": "red"}),
        ]
        cmd, best, ranked = self.pipeline.step(detections, (480, 640), self.joints, robot_id=1)

        self.assertIsNotNone(best)
        assert best is not None
        self.assertEqual(best.detection.label, "cone")
        self.assertGreater(len(ranked), 0)
        self.assertEqual(cmd.robot_id, 1)


if __name__ == "__main__":
    unittest.main()
