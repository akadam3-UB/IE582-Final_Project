"""Low-level steering/throttle controller for selected targets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .models import Detection, DriveCommand


@dataclass
class DriveControllerConfig:
    """Controller gains and limits in UB Racer user-scale units."""

    steering_gain: float = 0.25
    dead_zone_px: float = 16.0
    max_throttle_track: float = 32.0
    max_throttle_go_to: float = 45.0
    min_throttle: float = 10.0
    close_object_area_ratio: float = 0.18
    obstacle_steering_boost: float = 22.0
    obstacle_throttle_scale: float = 0.6


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class DriveController:
    """Convert selected target geometry into drive commands."""

    def __init__(self, config: Optional[DriveControllerConfig] = None) -> None:
        self.config = config or DriveControllerConfig()

    def compute_drive_command(
        self,
        target: Optional[Detection],
        frame_shape: Tuple[int, int],
        mode: str = "track",
        speed_scale: float = 1.0,
        obstacle_side: Optional[str] = None,
        stop: bool = False,
    ) -> DriveCommand:
        """Compute a steering/throttle command.

        Args:
            target: Chosen target detection, if any.
            frame_shape: (height, width) in pixels.
            mode: ``track`` or ``go_to``.
            speed_scale: external speed multiplier from command parsing.
            obstacle_side: ``left`` or ``right`` when obstacle is detected.
            stop: emergency stop flag.
        """

        if stop or target is None:
            return DriveCommand(
                steering=0.0,
                throttle=0.0,
                mode="stop" if stop else "idle",
                target_track_id=target.track_id if target else None,
                debug={"reason": 1.0},
            )

        frame_h, frame_w = frame_shape
        error_px = target.bbox.center_x - frame_w / 2.0

        if abs(error_px) <= self.config.dead_zone_px:
            error_px = 0.0

        steering = _clamp(error_px * self.config.steering_gain, -100.0, 100.0)

        base_throttle = (
            self.config.max_throttle_go_to if mode == "go_to" else self.config.max_throttle_track
        )
        base_throttle *= _clamp(speed_scale, 0.3, 1.5)

        turn_penalty = 1.0 - 0.7 * min(1.0, abs(steering) / 100.0)
        throttle = max(self.config.min_throttle, base_throttle * turn_penalty)

        # In go-to mode, slow down as target occupies a larger area in the frame.
        if mode == "go_to":
            frame_area = max(1.0, float(frame_h * frame_w))
            area_ratio = target.bbox.area / frame_area
            if area_ratio >= self.config.close_object_area_ratio:
                throttle = 0.0
            else:
                proximity_scale = 1.0 - (area_ratio / self.config.close_object_area_ratio)
                throttle *= _clamp(proximity_scale, 0.3, 1.0)

        if obstacle_side == "left":
            steering += self.config.obstacle_steering_boost
            throttle *= self.config.obstacle_throttle_scale
        elif obstacle_side == "right":
            steering -= self.config.obstacle_steering_boost
            throttle *= self.config.obstacle_throttle_scale

        steering = _clamp(steering, -100.0, 100.0)
        throttle = _clamp(throttle, -100.0, 100.0)

        debug = {
            "error_px": float(error_px),
            "base_throttle": float(base_throttle),
            "turn_penalty": float(turn_penalty),
        }

        return DriveCommand(
            steering=round(steering, 3),
            throttle=round(throttle, 3),
            mode=mode,
            target_track_id=target.track_id,
            debug=debug,
        )
