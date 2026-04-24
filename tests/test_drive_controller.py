from __future__ import annotations

import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ie582_final_project.drive_controller import DriveController
from ie582_final_project.models import BoundingBox, Detection


class DriveControllerTests(unittest.TestCase):
    def test_no_target_returns_idle_stop(self) -> None:
        controller = DriveController()
        cmd = controller.compute_drive_command(target=None, frame_shape=(480, 640))
        self.assertEqual(cmd.mode, "idle")
        self.assertEqual(cmd.steering, 0.0)
        self.assertEqual(cmd.throttle, 0.0)

    def test_go_to_slows_to_zero_when_target_is_close(self) -> None:
        controller = DriveController()
        # Very large box -> near the robot
        target = Detection(
            label="cone",
            confidence=0.9,
            track_id=5,
            bbox=BoundingBox(80, 40, 560, 460),
        )
        cmd = controller.compute_drive_command(target=target, frame_shape=(480, 640), mode="go_to")
        self.assertEqual(cmd.throttle, 0.0)

    def test_obstacle_left_biases_steering_right(self) -> None:
        controller = DriveController()
        target = Detection(
            label="person",
            confidence=0.9,
            track_id=3,
            bbox=BoundingBox(250, 160, 360, 410),
        )
        base = controller.compute_drive_command(target=target, frame_shape=(480, 640), mode="track")
        with_obstacle = controller.compute_drive_command(
            target=target,
            frame_shape=(480, 640),
            mode="track",
            obstacle_side="left",
        )
        self.assertGreater(with_obstacle.steering, base.steering)
        self.assertLess(with_obstacle.throttle, base.throttle)


if __name__ == "__main__":
    unittest.main()
