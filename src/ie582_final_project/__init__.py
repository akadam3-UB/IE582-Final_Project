"""Room 427 command-guided pan/tilt tracking package."""

from .command_parser import build_vlm_prompt, parse_command, parse_vlm_json
from .models import (
    BoundingBox,
    CommandIntent,
    Detection,
    JointState,
    PanTiltCommand,
    TargetScore,
)
from .pan_tilt_controller import PanTiltController, PanTiltControllerConfig
from .pan_tilt_pipeline import PanTiltPipelineConfig, PanTiltTargetingPipeline
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
    "JointState",
    "PanTiltCommand",
    "TargetScore",
    "PanTiltController",
    "PanTiltControllerConfig",
    "PanTiltPipelineConfig",
    "PanTiltTargetingPipeline",
    "FFmpegMicrophoneRecorder",
    "RuntimeCommandInputs",
    "TargetSelectorConfig",
    "WhisperAudioTranscriber",
    "build_scene_summary",
    "build_vlm_prompt",
    "estimate_detection_attributes",
    "list_macos_audio_devices",
    "parse_command",
    "parse_vlm_json",
    "rank_targets",
    "select_target",
    "top_labels",
    "ultralytics_results_to_detections",
]
