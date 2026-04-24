"""Shared data models for the IE582 final project pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned bounding box in pixel coordinates."""

    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center_x(self) -> float:
        return self.x1 + self.width / 2.0

    @property
    def center_y(self) -> float:
        return self.y1 + self.height / 2.0


@dataclass(frozen=True)
class Detection:
    """A single tracked object candidate."""

    label: str
    confidence: float
    bbox: BoundingBox
    track_id: Optional[int] = None
    attributes: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CommandIntent:
    """Parsed command for target selection and motion mode."""

    action: str = "track"  # track | go_to | stop
    target_label: Optional[str] = None
    target_color: Optional[str] = None
    target_region: Optional[str] = None
    target_track_id: Optional[int] = None
    speed_scale: float = 1.0
    priority_hint: Optional[str] = None
    raw_text: str = ""


@dataclass(frozen=True)
class TargetScore:
    """Ranking output for one detection."""

    detection: Detection
    total: float
    breakdown: Dict[str, float]
    reason: str


@dataclass(frozen=True)
class DriveCommand:
    """Low-level drive output in UB Racer control scale."""

    steering: float
    throttle: float
    mode: str
    target_track_id: Optional[int] = None
    debug: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class JointState:
    """Runtime state and limits for one pan/tilt joint."""

    angle_deg: float
    min_angle: float
    max_angle: float
    ok: bool = True
    torque: bool = True

    @staticmethod
    def from_status_dict(data: Dict[str, object]) -> "JointState":
        """Build from host `status` payload shape."""

        return JointState(
            angle_deg=float(data.get("angle_deg", 0.0)),
            min_angle=float(data.get("min_angle", -180.0)),
            max_angle=float(data.get("max_angle", 180.0)),
            ok=bool(data.get("OK", True)),
            torque=bool(data.get("torque", True)),
        )


@dataclass(frozen=True)
class PanTiltCommand:
    """Pan/tilt target command in host socket format."""

    joint_targets: Dict[str, float]
    robot_id: Optional[int] = None
    target_track_id: Optional[int] = None
    debug: Dict[str, float] = field(default_factory=dict)

    @property
    def has_update(self) -> bool:
        return bool(self.joint_targets)

    def to_host_payload(self) -> Optional[list]:
        """Format for `sio_host.emit('command', [robotID, [cmd]])`."""

        if self.robot_id is None or not self.joint_targets:
            return None
        return [self.robot_id, [self.joint_targets]]
