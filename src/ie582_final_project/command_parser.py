"""Command parsing utilities for voice/text robot instructions."""

from __future__ import annotations

import json
import re
from typing import Dict, Optional

from .models import CommandIntent


COLOR_WORDS = {
    "red",
    "blue",
    "green",
    "yellow",
    "orange",
    "purple",
    "white",
    "black",
    "gray",
    "grey",
    "pink",
    "brown",
}

REGION_WORDS = {
    "left": "left",
    "left side": "left",
    "right": "right",
    "right side": "right",
    "center": "center",
    "centre": "center",
    "middle": "center",
}

LABEL_SYNONYMS = {
    "person": {"person", "human", "man", "woman", "student", "teacher", "professor", "instructor"},
    "cone": {"cone", "traffic cone"},
    "car": {"car", "vehicle", "robot car"},
    "bottle": {"bottle", "water bottle"},
    "chair": {"chair", "seat"},
    "backpack": {"backpack", "bag"},
    "ball": {"ball"},
    "box": {"box", "package"},
    "dog": {"dog"},
    "cat": {"cat"},
}


def build_vlm_prompt(scene_description: str, user_command: str) -> str:
    """Build a constrained prompt for a VLM/NLM command grounding step."""

    return (
        "You are grounding a robot command into structured JSON.\\n"
        "Return ONLY JSON with keys: "
        "action, target_label, target_color, target_region, target_track_id, speed_scale, priority_hint.\\n"
        "Allowed action values: track, go_to, stop.\\n"
        "speed_scale must be a float in [0.3, 1.5].\\n"
        "Set unknown fields to null.\\n\\n"
        f"Scene: {scene_description}\\n"
        f"Command: {user_command}"
    )


def _extract_balanced_json_blob(text: str) -> Optional[str]:
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _canonical_label(raw: str) -> Optional[str]:
    token = raw.strip().lower()
    for canonical, synonyms in LABEL_SYNONYMS.items():
        if token in synonyms:
            return canonical
    return None


def _extract_label(text: str) -> Optional[str]:
    normalized = text.lower()
    for canonical, synonyms in LABEL_SYNONYMS.items():
        for word in synonyms:
            if re.search(rf"\b{re.escape(word)}\b", normalized):
                return canonical
    return None


def _extract_color(text: str) -> Optional[str]:
    normalized = text.lower()
    for color in COLOR_WORDS:
        if re.search(rf"\b{re.escape(color)}\b", normalized):
            return "gray" if color == "grey" else color
    return None


def _extract_region(text: str) -> Optional[str]:
    normalized = text.lower()
    for phrase, canonical in sorted(REGION_WORDS.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"\b{re.escape(phrase)}\b", normalized):
            return canonical
    return None


def _intent_from_mapping(data: Dict[str, object], raw_text: str) -> CommandIntent:
    action_raw = str(data.get("action", "track")).strip().lower()
    action = action_raw if action_raw in {"track", "go_to", "stop"} else "track"

    label_value = data.get("target_label")
    target_label = _canonical_label(str(label_value)) if label_value else None

    color_value = data.get("target_color")
    target_color = str(color_value).strip().lower() if color_value else None
    if target_color == "grey":
        target_color = "gray"
    if target_color and target_color not in {("gray" if color == "grey" else color) for color in COLOR_WORDS}:
        target_color = None

    region_value = data.get("target_region")
    target_region = str(region_value).strip().lower() if region_value else None
    if target_region == "centre":
        target_region = "center"
    if target_region and target_region not in {"left", "right", "center"}:
        target_region = None

    track_id = data.get("target_track_id")
    if track_id is not None:
        try:
            track_id = int(track_id)
        except (TypeError, ValueError):
            track_id = None

    speed_scale = data.get("speed_scale", 1.0)
    try:
        speed_scale = float(speed_scale)
    except (TypeError, ValueError):
        speed_scale = 1.0
    speed_scale = max(0.3, min(1.5, speed_scale))

    priority_hint_value = data.get("priority_hint")
    priority_hint = str(priority_hint_value).strip() if priority_hint_value else None

    return CommandIntent(
        action=action,
        target_label=target_label,
        target_color=target_color,
        target_region=target_region,
        target_track_id=track_id,
        speed_scale=speed_scale,
        priority_hint=priority_hint,
        raw_text=raw_text,
    )


def parse_vlm_json(vlm_text: str, raw_text: str = "") -> Optional[CommandIntent]:
    """Parse JSON emitted by a VLM/NLM response."""

    blob = _extract_balanced_json_blob(vlm_text)
    if not blob:
        return None

    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None
    return _intent_from_mapping(data, raw_text=raw_text)


def parse_rule_based(command_text: str) -> CommandIntent:
    """Lightweight rule-based parser for local/offline command understanding."""

    text = command_text.strip()
    normalized = text.lower()

    action = "track"
    if any(token in normalized for token in ("stop", "halt", "cancel", "freeze")):
        action = "stop"
    elif any(token in normalized for token in ("go to", "goto", "approach", "move to", "drive to")):
        action = "go_to"

    track_match = re.search(r"(?:track|id)\s*#?\s*(\d+)", normalized)
    target_track_id = int(track_match.group(1)) if track_match else None

    speed_scale = 1.0
    if any(token in normalized for token in ("slower", "slow", "careful")):
        speed_scale = 0.65
    elif any(token in normalized for token in ("faster", "fast", "quick")):
        speed_scale = 1.2

    priority_hint = None
    if "closest" in normalized and "center" in normalized:
        priority_hint = "closest_to_center"
    elif "biggest" in normalized or "largest" in normalized:
        priority_hint = "largest"
    elif "highest confidence" in normalized:
        priority_hint = "highest_confidence"

    return CommandIntent(
        action=action,
        target_label=_extract_label(normalized),
        target_color=_extract_color(normalized),
        target_region=_extract_region(normalized),
        target_track_id=target_track_id,
        speed_scale=speed_scale,
        priority_hint=priority_hint,
        raw_text=text,
    )


def merge_intents(base: CommandIntent, override: CommandIntent) -> CommandIntent:
    """Merge rule-based and VLM intents, preferring explicit override fields."""

    return CommandIntent(
        action=override.action or base.action,
        target_label=override.target_label or base.target_label,
        target_color=override.target_color or base.target_color,
        target_region=override.target_region or base.target_region,
        target_track_id=(
            override.target_track_id
            if override.target_track_id is not None
            else base.target_track_id
        ),
        speed_scale=override.speed_scale if override.speed_scale != 1.0 else base.speed_scale,
        priority_hint=override.priority_hint or base.priority_hint,
        raw_text=base.raw_text,
    )


def parse_command(command_text: str, vlm_text: Optional[str] = None) -> CommandIntent:
    """Parse text command into a normalized intent.

    If ``vlm_text`` is provided and contains parseable JSON, VLM fields are merged
    on top of rule-based extraction.
    """

    base = parse_rule_based(command_text)
    if not vlm_text:
        return base

    vlm_intent = parse_vlm_json(vlm_text, raw_text=command_text)
    if vlm_intent is None:
        return base
    return merge_intents(base, vlm_intent)
