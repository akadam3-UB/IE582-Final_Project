"""End-to-end command-grounded pipeline for pan/tilt camera tracking."""

from __future__ import annotations

from typing import Iterable, List, Mapping, Optional, Tuple

from .command_parser import parse_command
from .models import CommandIntent, Detection, PanTiltCommand, TargetScore
from .pan_tilt_controller import PanTiltController, PanTiltControllerConfig
from .target_selector import TargetSelectorConfig, rank_targets, select_target


class PanTiltTargetingPipeline:
    """Stateful pan/tilt targeting pipeline.

    Uses the same command parser and target selector as the generic pipeline, then
    emits pan/tilt joint commands compatible with the course host socket API.
    """

    def __init__(
        self,
        selector_config: Optional[TargetSelectorConfig] = None,
        controller_config: Optional[PanTiltControllerConfig] = None,
    ) -> None:
        self.selector_config = selector_config or TargetSelectorConfig()
        self.controller = PanTiltController(controller_config)

        self.intent = CommandIntent(action="track")
        self.last_ranked: List[TargetScore] = []
        self.active_track_id: Optional[int] = None

    def update_command(self, command_text: str, vlm_text: Optional[str] = None) -> CommandIntent:
        """Update active intent from user command text and optional VLM JSON."""

        self.intent = parse_command(command_text, vlm_text=vlm_text)
        self.active_track_id = self.intent.target_track_id
        return self.intent

    def step(
        self,
        detections: Iterable[Detection],
        frame_shape: Tuple[int, int],
        joint_state: Mapping[str, object],
        robot_id: Optional[int] = None,
        emergency_stop: bool = False,
    ) -> Tuple[PanTiltCommand, Optional[TargetScore], List[TargetScore]]:
        """Run one pan/tilt control cycle."""

        if self.intent.action == "stop":
            cmd = self.controller.compute_command(
                target=None,
                frame_shape=frame_shape,
                joint_state=joint_state,
                robot_id=robot_id,
                speed_scale=self.intent.speed_scale,
                stop=True,
            )
            self.last_ranked = []
            self.active_track_id = None
            return cmd, None, []

        sticky_track_id = None
        if self.intent.target_track_id is None:
            sticky_track_id = self.active_track_id

        best = select_target(
            detections=detections,
            intent=self.intent,
            frame_shape=frame_shape,
            config=self.selector_config,
            sticky_track_id=sticky_track_id,
        )

        self.last_ranked = rank_targets(
            detections=detections,
            intent=self.intent,
            frame_shape=frame_shape,
            config=self.selector_config,
            sticky_track_id=sticky_track_id,
        )

        if best is not None and best.detection.track_id is not None:
            self.active_track_id = best.detection.track_id

        cmd = self.controller.compute_command(
            target=best.detection if best else None,
            frame_shape=frame_shape,
            joint_state=joint_state,
            robot_id=robot_id,
            speed_scale=self.intent.speed_scale,
            stop=emergency_stop,
        )

        return cmd, best, self.last_ranked
