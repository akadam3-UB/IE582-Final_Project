from __future__ import annotations

import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ie582_final_project.models import BoundingBox, Detection
from ie582_final_project.pan_tilt_pipeline import PanTiltPipelineConfig, PanTiltTargetingPipeline
from ie582_final_project.target_selector import TargetSelectorConfig


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

    def test_pipeline_holds_current_target_when_challenger_is_only_slightly_better(self) -> None:
        pipeline = PanTiltTargetingPipeline(
            selector_config=TargetSelectorConfig(sticky_track_bonus=0.0),
            pipeline_config=PanTiltPipelineConfig(switch_margin=0.20),
        )
        pipeline.update_command("track the person")

        first_frame = [
            Detection("person", 0.90, BoundingBox(240, 90, 380, 420), track_id=7),
        ]
        _, first_best, _ = pipeline.step(first_frame, (480, 640), self.joints, robot_id=1)
        self.assertIsNotNone(first_best)
        assert first_best is not None
        self.assertEqual(first_best.detection.track_id, 7)

        second_frame = [
            Detection("person", 0.90, BoundingBox(220, 90, 360, 420), track_id=7),
            Detection("person", 0.93, BoundingBox(250, 90, 390, 420), track_id=9),
        ]
        _, second_best, ranked = pipeline.step(second_frame, (480, 640), self.joints, robot_id=1)
        self.assertIsNotNone(second_best)
        assert second_best is not None
        self.assertEqual(ranked[0].detection.track_id, 9)
        self.assertEqual(second_best.detection.track_id, 7)

    def test_pipeline_switches_when_new_target_is_clearly_better(self) -> None:
        pipeline = PanTiltTargetingPipeline(
            selector_config=TargetSelectorConfig(sticky_track_bonus=0.0),
            pipeline_config=PanTiltPipelineConfig(switch_margin=0.10),
        )
        pipeline.update_command("track the person")

        first_frame = [
            Detection("person", 0.88, BoundingBox(150, 110, 290, 420), track_id=4),
        ]
        pipeline.step(first_frame, (480, 640), self.joints, robot_id=1)

        second_frame = [
            Detection("person", 0.82, BoundingBox(60, 110, 180, 360), track_id=4),
            Detection("person", 0.97, BoundingBox(250, 100, 430, 450), track_id=6),
        ]
        _, second_best, ranked = pipeline.step(second_frame, (480, 640), self.joints, robot_id=1)
        self.assertIsNotNone(second_best)
        assert second_best is not None
        self.assertEqual(ranked[0].detection.track_id, 6)
        self.assertEqual(second_best.detection.track_id, 6)


if __name__ == "__main__":
    unittest.main()
