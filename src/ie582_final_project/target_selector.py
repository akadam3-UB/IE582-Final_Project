"""Target prioritization logic for multi-object tracking."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from .models import CommandIntent, Detection, TargetScore


@dataclass
class TargetSelectorConfig:
    """Weights and priors for target ranking."""

    weight_center: float = 0.35
    weight_size: float = 0.20
    weight_confidence: float = 0.25
    weight_class_priority: float = 0.20
    min_confidence: float = 0.10
    label_match_bonus: float = 0.15
    label_mismatch_penalty: float = 0.35
    color_match_bonus: float = 0.20
    color_mismatch_penalty: float = 0.12
    region_match_bonus: float = 0.12
    region_mismatch_penalty: float = 0.08
    track_id_match_bonus: float = 0.60
    track_id_mismatch_penalty: float = 1.00
    sticky_track_bonus: float = 0.18
    class_priority: Dict[str, float] = field(
        default_factory=lambda: {
            "person": 1.00,
            "cone": 0.90,
            "car": 0.85,
            "bottle": 0.60,
            "chair": 0.55,
            "backpack": 0.55,
            "ball": 0.55,
            "box": 0.50,
            "dog": 0.80,
            "cat": 0.80,
        }
    )


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _center_score(detection: Detection, frame_shape: Tuple[int, int]) -> float:
    frame_h, frame_w = frame_shape
    cx = detection.bbox.center_x
    cy = detection.bbox.center_y
    dx = cx - frame_w / 2.0
    dy = cy - frame_h / 2.0
    distance = math.hypot(dx, dy)
    max_distance = math.hypot(frame_w / 2.0, frame_h / 2.0)
    if max_distance <= 0:
        return 0.0
    return _clamp(1.0 - distance / max_distance, 0.0, 1.0)


def _size_score(detection: Detection, frame_shape: Tuple[int, int]) -> float:
    frame_h, frame_w = frame_shape
    frame_area = max(1.0, float(frame_h * frame_w))
    area_ratio = detection.bbox.area / frame_area
    # Saturate at 25% image area to avoid oversized-object domination.
    return _clamp(area_ratio / 0.25, 0.0, 1.0)


def _class_priority_score(detection: Detection, config: TargetSelectorConfig) -> float:
    return _clamp(config.class_priority.get(detection.label.lower(), 0.50), 0.0, 1.0)


def _priority_hint_bonus(
    intent: CommandIntent,
    center_score: float,
    size_score: float,
    confidence_score: float,
) -> float:
    if intent.priority_hint == "closest_to_center":
        return 0.25 * center_score
    if intent.priority_hint == "largest":
        return 0.25 * size_score
    if intent.priority_hint == "highest_confidence":
        return 0.25 * confidence_score
    return 0.0


def _region_for_detection(detection: Detection, frame_shape: Tuple[int, int]) -> str:
    _, frame_w = frame_shape
    if frame_w <= 0:
        return "center"

    center_x = detection.bbox.center_x
    if center_x < frame_w / 3.0:
        return "left"
    if center_x > 2.0 * frame_w / 3.0:
        return "right"
    return "center"


def _command_match_adjustment(
    detection: Detection,
    intent: CommandIntent,
    config: TargetSelectorConfig,
    frame_shape: Tuple[int, int],
    sticky_track_id: Optional[int],
) -> Tuple[float, Dict[str, float]]:
    adjustment = 0.0
    detail: Dict[str, float] = {}

    if intent.target_label:
        if detection.label.lower() == intent.target_label.lower():
            adjustment += config.label_match_bonus
            detail["label_match"] = config.label_match_bonus
        else:
            adjustment -= config.label_mismatch_penalty
            detail["label_mismatch"] = -config.label_mismatch_penalty

    if intent.target_color:
        observed_color = detection.attributes.get("color", "").strip().lower()
        if observed_color and observed_color == intent.target_color.lower():
            adjustment += config.color_match_bonus
            detail["color_match"] = config.color_match_bonus
        elif observed_color:
            adjustment -= config.color_mismatch_penalty
            detail["color_mismatch"] = -config.color_mismatch_penalty

    if intent.target_region:
        observed_region = _region_for_detection(detection, frame_shape)
        if observed_region == intent.target_region:
            adjustment += config.region_match_bonus
            detail["region_match"] = config.region_match_bonus
        else:
            adjustment -= config.region_mismatch_penalty
            detail["region_mismatch"] = -config.region_mismatch_penalty

    if intent.target_track_id is not None:
        if detection.track_id == intent.target_track_id:
            adjustment += config.track_id_match_bonus
            detail["track_id_match"] = config.track_id_match_bonus
        else:
            adjustment -= config.track_id_mismatch_penalty
            detail["track_id_mismatch"] = -config.track_id_mismatch_penalty
    elif sticky_track_id is not None and detection.track_id == sticky_track_id:
        adjustment += config.sticky_track_bonus
        detail["sticky_track"] = config.sticky_track_bonus

    return adjustment, detail


def rank_targets(
    detections: Iterable[Detection],
    intent: CommandIntent,
    frame_shape: Tuple[int, int],
    config: Optional[TargetSelectorConfig] = None,
    sticky_track_id: Optional[int] = None,
) -> List[TargetScore]:
    """Rank candidate detections from best to worst for the given intent."""

    cfg = config or TargetSelectorConfig()
    ranked: List[TargetScore] = []

    for detection in detections:
        if detection.confidence < cfg.min_confidence:
            continue

        center_score = _center_score(detection, frame_shape)
        size_score = _size_score(detection, frame_shape)
        confidence_score = _clamp(detection.confidence, 0.0, 1.0)
        class_score = _class_priority_score(detection, cfg)

        breakdown = {
            "center": cfg.weight_center * center_score,
            "size": cfg.weight_size * size_score,
            "confidence": cfg.weight_confidence * confidence_score,
            "class_priority": cfg.weight_class_priority * class_score,
        }

        base_total = sum(breakdown.values())

        hint_bonus = _priority_hint_bonus(intent, center_score, size_score, confidence_score)
        if hint_bonus:
            breakdown["priority_hint"] = hint_bonus

        command_adjust, match_detail = _command_match_adjustment(
            detection,
            intent,
            cfg,
            frame_shape=frame_shape,
            sticky_track_id=sticky_track_id,
        )
        breakdown.update(match_detail)

        total = base_total + hint_bonus + command_adjust

        reason_parts = sorted(breakdown.items(), key=lambda item: item[1], reverse=True)
        reason = ", ".join(f"{name}={value:.2f}" for name, value in reason_parts[:3])

        ranked.append(
            TargetScore(
                detection=detection,
                total=total,
                breakdown={k: round(v, 4) for k, v in breakdown.items()},
                reason=reason,
            )
        )

    ranked.sort(key=lambda score: score.total, reverse=True)
    return ranked


def select_target(
    detections: Iterable[Detection],
    intent: CommandIntent,
    frame_shape: Tuple[int, int],
    config: Optional[TargetSelectorConfig] = None,
    sticky_track_id: Optional[int] = None,
) -> Optional[TargetScore]:
    """Return the highest-ranked target, if any."""

    ranked = rank_targets(
        detections=detections,
        intent=intent,
        frame_shape=frame_shape,
        config=config,
        sticky_track_id=sticky_track_id,
    )
    if not ranked:
        return None
    return ranked[0]
