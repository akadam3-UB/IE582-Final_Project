"""End-to-end command-grounded pipeline for pan/tilt camera tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Mapping, Optional, Tuple

from .command_parser import parse_command
from .models import CommandIntent, Detection, PanTiltCommand, TargetScore
from .pan_tilt_controller import PanTiltController, PanTiltControllerConfig
from .target_selector import TargetSelectorConfig, rank_targets


@dataclass
class PanTiltPipelineConfig:
    """Pipeline-level behavior for selection stability.

    ``min_accept_score`` avoids committing to weak targets when the ranking signal
    is poor. ``switch_margin`` adds hysteresis so we do not bounce between nearly
    equivalent candidates when multiple objects satisfy the same command.
    """

    min_accept_score: float = 0.20
    switch_margin: float = 0.12


class PanTiltTargetingPipeline:
    """Stateful pan/tilt targeting pipeline.

    Uses the same command parser and target selector as the generic pipeline, then
    emits pan/tilt joint commands compatible with the course host socket API.
    """

    def __init__(
        self,
        selector_config: Optional[TargetSelectorConfig] = None,
        controller_config: Optional[PanTiltControllerConfig] = None,
        pipeline_config: Optional[PanTiltPipelineConfig] = None,
    ) -> None:
        self.selector_config = selector_config or TargetSelectorConfig()
        self.controller = PanTiltController(controller_config)
        self.pipeline_config = pipeline_config or PanTiltPipelineConfig()

        self.intent = CommandIntent(action="track")
        self.last_ranked: List[TargetScore] = []
        self.active_track_id: Optional[int] = None

    def update_command(self, command_text: str, vlm_text: Optional[str] = None) -> CommandIntent:
        """Update active intent from user command text and optional VLM JSON."""

        self.intent = parse_command(command_text, vlm_text=vlm_text)
        self.active_track_id = self.intent.target_track_id
        return self.intent

    def _stabilize_selection(self, ranked: List[TargetScore]) -> Optional[TargetScore]:
        if not ranked:
            return None

        best = ranked[0]
        if best.total < self.pipeline_config.min_accept_score:
            return None

        if self.active_track_id is None:
            return best

        active_score = next(
            (score for score in ranked if score.detection.track_id == self.active_track_id),
            None,
        )
        if active_score is None:
            return best

        if best.detection.track_id == self.active_track_id:
            return best

        if best.total >= active_score.total + self.pipeline_config.switch_margin:
            return best

        return active_score

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

        self.last_ranked = rank_targets(
            detections=detections,
            intent=self.intent,
            frame_shape=frame_shape,
            config=self.selector_config,
            sticky_track_id=self.active_track_id if self.intent.target_track_id is None else None,
        )
        best = self._stabilize_selection(self.last_ranked)

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
