"""Pan/tilt joint controller for visual target lock."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

from .models import Detection, JointState, PanTiltCommand


@dataclass
class PanTiltControllerConfig:
    """Controller tuning for 2-DOF pan/tilt camera."""

    pan_joint_name: str = "arm_shoulder_pan_joint"
    tilt_joint_name: str = "arm_shoulder_lift_joint"
    pan_deadband_px: float = 5.0
    tilt_deadband_px: float = 5.0
    pan_fov_deg: float = 41.4
    tilt_fov_deg: float = 31.6
    gain_scale: float = 1.0
    min_step_deg: float = 0.05


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _as_joint_state(raw: object) -> Optional[JointState]:
    if raw is None:
        return None
    if isinstance(raw, JointState):
        return raw
    if isinstance(raw, Mapping):
        return JointState.from_status_dict(dict(raw))
    return None


class PanTiltController:
    """Convert image-space error into pan/tilt joint angle commands.

    Error convention follows the class reference implementation:
    - ``error_x = frame_center_x - target_center_x`` (>0 means target is left)
    - ``error_y = target_center_y - frame_center_y`` (>0 means target is below)

    With the default robot geometry:
    - increasing pan angle rotates camera left
    - increasing tilt angle rotates camera down
    """

    def __init__(self, config: Optional[PanTiltControllerConfig] = None) -> None:
        self.config = config or PanTiltControllerConfig()

    def compute_command(
        self,
        target: Optional[Detection],
        frame_shape: Tuple[int, int],
        joint_state: Mapping[str, object],
        robot_id: Optional[int] = None,
        speed_scale: float = 1.0,
        stop: bool = False,
    ) -> PanTiltCommand:
        """Compute pan/tilt command for current target.

        Args:
            target: selected detection or ``None``.
            frame_shape: ``(height, width)``.
            joint_state: mapping keyed by joint name with either ``JointState``
                or raw host payload dicts.
            robot_id: optional robot ID used for host payload formatting.
            speed_scale: external command gain scale (from parser intent).
            stop: when true, returns an empty command.
        """

        if stop or target is None:
            return PanTiltCommand(
                joint_targets={},
                robot_id=robot_id,
                target_track_id=target.track_id if target else None,
                debug={"stopped": 1.0 if stop else 0.0},
            )

        frame_h, frame_w = frame_shape
        if frame_h <= 0 or frame_w <= 0:
            return PanTiltCommand(
                joint_targets={},
                robot_id=robot_id,
                target_track_id=target.track_id,
                debug={"invalid_frame": 1.0},
            )

        pan_joint = _as_joint_state(joint_state.get(self.config.pan_joint_name))
        tilt_joint = _as_joint_state(joint_state.get(self.config.tilt_joint_name))
        if pan_joint is None and tilt_joint is None:
            return PanTiltCommand(
                joint_targets={},
                robot_id=robot_id,
                target_track_id=target.track_id,
                debug={"missing_joint_state": 1.0},
            )

        speed_scale = _clamp(float(speed_scale), 0.3, 1.5)

        error_x = frame_w / 2.0 - target.bbox.center_x
        error_y = target.bbox.center_y - frame_h / 2.0

        cmd = {}
        debug = {
            "error_x_px": float(error_x),
            "error_y_px": float(error_y),
        }

        if pan_joint is not None and abs(error_x) > self.config.pan_deadband_px:
            pan_delta = (
                (error_x / (frame_w / 2.0))
                * (self.config.pan_fov_deg / 2.0)
                * self.config.gain_scale
                * speed_scale
            )
            debug["pan_delta_deg"] = float(pan_delta)
            if abs(pan_delta) >= self.config.min_step_deg:
                pan_target = _clamp(
                    pan_joint.angle_deg + pan_delta,
                    pan_joint.min_angle,
                    pan_joint.max_angle,
                )
                cmd[self.config.pan_joint_name] = round(pan_target, 4)

        if tilt_joint is not None and abs(error_y) > self.config.tilt_deadband_px:
            tilt_delta = (
                (error_y / (frame_h / 2.0))
                * (self.config.tilt_fov_deg / 2.0)
                * self.config.gain_scale
                * speed_scale
            )
            debug["tilt_delta_deg"] = float(tilt_delta)
            if abs(tilt_delta) >= self.config.min_step_deg:
                tilt_target = _clamp(
                    tilt_joint.angle_deg + tilt_delta,
                    tilt_joint.min_angle,
                    tilt_joint.max_angle,
                )
                cmd[self.config.tilt_joint_name] = round(tilt_target, 4)

        return PanTiltCommand(
            joint_targets=cmd,
            robot_id=robot_id,
            target_track_id=target.track_id,
            debug=debug,
        )
