"""Starter package for IE582 multi-target prioritization and control."""

from .command_parser import parse_command
from .drive_controller import DriveController, DriveControllerConfig
from .models import (
    BoundingBox,
    CommandIntent,
    Detection,
    DriveCommand,
    JointState,
    PanTiltCommand,
    TargetScore,
)
from .pan_tilt_controller import PanTiltController, PanTiltControllerConfig
from .pan_tilt_pipeline import PanTiltPipelineConfig, PanTiltTargetingPipeline
from .pipeline import MultiTargetPipeline
from .runtime_inputs import (
    FFmpegMicrophoneRecorder,
    RuntimeCommandInputs,
    WhisperAudioTranscriber,
    list_macos_audio_devices,
)
from .target_selector import TargetSelectorConfig, rank_targets, select_target
from .vision import (
    build_scene_summary,
    estimate_detection_attributes,
    top_labels,
    ultralytics_results_to_detections,
)

__all__ = [
    "BoundingBox",
    "CommandIntent",
    "Detection",
    "DriveCommand",
    "JointState",
    "PanTiltCommand",
    "TargetScore",
    "DriveController",
    "DriveControllerConfig",
    "PanTiltController",
    "PanTiltControllerConfig",
    "PanTiltPipelineConfig",
    "PanTiltTargetingPipeline",
    "FFmpegMicrophoneRecorder",
    "RuntimeCommandInputs",
    "TargetSelectorConfig",
    "MultiTargetPipeline",
    "WhisperAudioTranscriber",
    "build_scene_summary",
    "estimate_detection_attributes",
    "list_macos_audio_devices",
    "parse_command",
    "rank_targets",
    "select_target",
    "top_labels",
    "ultralytics_results_to_detections",
]
