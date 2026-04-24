"""End-to-end orchestration: command -> target selection -> drive command."""

from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

from .command_parser import parse_command
from .drive_controller import DriveController, DriveControllerConfig
from .models import CommandIntent, Detection, DriveCommand, TargetScore
from .target_selector import TargetSelectorConfig, rank_targets, select_target


class MultiTargetPipeline:
    """High-level stateful pipeline for command-grounded target tracking."""

    def __init__(
        self,
        selector_config: Optional[TargetSelectorConfig] = None,
        controller_config: Optional[DriveControllerConfig] = None,
    ) -> None:
        self.selector_config = selector_config or TargetSelectorConfig()
        self.controller = DriveController(controller_config)

        self.intent = CommandIntent(action="track")
        self.last_ranked: List[TargetScore] = []

    def update_command(self, command_text: str, vlm_text: Optional[str] = None) -> CommandIntent:
        """Update active intent from text (and optional VLM JSON text)."""

        self.intent = parse_command(command_text, vlm_text=vlm_text)
        return self.intent

    def step(
        self,
        detections: Iterable[Detection],
        frame_shape: Tuple[int, int],
        obstacle_side: Optional[str] = None,
        emergency_stop: bool = False,
    ) -> Tuple[DriveCommand, Optional[TargetScore], List[TargetScore]]:
        """Run one control cycle.

        Returns:
            (drive_command, best_target, full_ranking)
        """

        if self.intent.action == "stop":
            cmd = self.controller.compute_drive_command(
                target=None,
                frame_shape=frame_shape,
                mode="track",
                speed_scale=self.intent.speed_scale,
                obstacle_side=obstacle_side,
                stop=True,
            )
            self.last_ranked = []
            return cmd, None, []

        best = select_target(
            detections=detections,
            intent=self.intent,
            frame_shape=frame_shape,
            config=self.selector_config,
        )

        self.last_ranked = rank_targets(
            detections=detections,
            intent=self.intent,
            frame_shape=frame_shape,
            config=self.selector_config,
        )

        mode = "go_to" if self.intent.action == "go_to" else "track"

        drive = self.controller.compute_drive_command(
            target=best.detection if best else None,
            frame_shape=frame_shape,
            mode=mode,
            speed_scale=self.intent.speed_scale,
            obstacle_side=obstacle_side,
            stop=emergency_stop,
        )
        return drive, best, self.last_ranked
