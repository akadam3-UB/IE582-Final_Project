from __future__ import annotations

import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ie582_final_project.models import BoundingBox, Detection
from ie582_final_project.pan_tilt_controller import PanTiltController, PanTiltControllerConfig


class PanTiltControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = PanTiltController()
        self.joints = {
            "arm_shoulder_pan_joint": {
                "angle_deg": 57.0,
                "min_angle": 0.0,
                "max_angle": 114.0,
                "OK": True,
                "torque": True,
            },
            "arm_shoulder_lift_joint": {
                "angle_deg": 125.0,
                "min_angle": 45.0,
                "max_angle": 160.0,
                "OK": True,
                "torque": True,
            },
        }

    def test_target_left_increases_pan_angle(self) -> None:
        target = Detection(
            label="person",
            confidence=0.9,
            track_id=7,
            bbox=BoundingBox(80, 120, 220, 420),
        )
        cmd = self.controller.compute_command(target, (480, 640), self.joints, robot_id=1)
        self.assertIn("arm_shoulder_pan_joint", cmd.joint_targets)
        self.assertGreater(cmd.joint_targets["arm_shoulder_pan_joint"], 57.0)

    def test_target_below_increases_tilt_angle(self) -> None:
        target = Detection(
            label="cone",
            confidence=0.9,
            track_id=2,
            bbox=BoundingBox(280, 280, 360, 470),
        )
        cmd = self.controller.compute_command(target, (480, 640), self.joints, robot_id=1)
        self.assertIn("arm_shoulder_lift_joint", cmd.joint_targets)
        self.assertGreater(cmd.joint_targets["arm_shoulder_lift_joint"], 125.0)

    def test_centered_target_generates_no_update(self) -> None:
        target = Detection(
            label="cone",
            confidence=0.9,
            track_id=2,
            bbox=BoundingBox(300, 220, 340, 260),
        )
        cmd = self.controller.compute_command(target, (480, 640), self.joints, robot_id=1)
        self.assertFalse(cmd.has_update)

    def test_joint_limits_are_enforced(self) -> None:
        target = Detection(
            label="person",
            confidence=0.9,
            track_id=3,
            bbox=BoundingBox(0, 0, 40, 120),
        )
        joints = {
            "arm_shoulder_pan_joint": {
                "angle_deg": 113.9,
                "min_angle": 0.0,
                "max_angle": 114.0,
            },
            "arm_shoulder_lift_joint": {
                "angle_deg": 125.0,
                "min_angle": 45.0,
                "max_angle": 160.0,
            },
        }
        cmd = self.controller.compute_command(target, (480, 640), joints, robot_id=1)
        self.assertLessEqual(cmd.joint_targets.get("arm_shoulder_pan_joint", 0.0), 114.0)

    def test_host_payload_format(self) -> None:
        target = Detection(
            label="cone",
            confidence=0.9,
            track_id=8,
            bbox=BoundingBox(80, 120, 220, 420),
        )
        cmd = self.controller.compute_command(target, (480, 640), self.joints, robot_id=4)
        payload = cmd.to_host_payload()
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload[0], 4)
        self.assertEqual(len(payload[1]), 1)
        self.assertIsInstance(payload[1][0], dict)

    def test_large_error_is_rate_limited(self) -> None:
        controller = PanTiltController(PanTiltControllerConfig(max_step_deg=1.0))
        target = Detection(
            label="person",
            confidence=0.9,
            track_id=5,
            bbox=BoundingBox(0, 0, 40, 80),
        )
        cmd = controller.compute_command(target, (480, 640), self.joints, robot_id=1)
        self.assertIn("arm_shoulder_pan_joint", cmd.joint_targets)
        self.assertLessEqual(cmd.joint_targets["arm_shoulder_pan_joint"] - 57.0, 1.0)
        self.assertGreater(cmd.debug["pan_delta_deg_raw"], cmd.debug["pan_delta_deg"])


if __name__ == "__main__":
    unittest.main()
