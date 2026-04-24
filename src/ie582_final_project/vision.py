"""Helpers for converting detector outputs into project data models."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from .models import BoundingBox, Detection


def _clip_bbox_to_frame(bbox: BoundingBox, frame_shape: Tuple[int, int]) -> Optional[Tuple[int, int, int, int]]:
    frame_h, frame_w = frame_shape[:2]
    x1 = max(0, min(frame_w, int(round(bbox.x1))))
    y1 = max(0, min(frame_h, int(round(bbox.y1))))
    x2 = max(0, min(frame_w, int(round(bbox.x2))))
    y2 = max(0, min(frame_h, int(round(bbox.y2))))

    if x2 <= x1 or y2 <= y1:
        return None
    return x1, y1, x2, y2


def _representative_crop(frame: np.ndarray, bbox: BoundingBox, inner_fraction: float = 0.55) -> Optional[np.ndarray]:
    coords = _clip_bbox_to_frame(bbox, frame.shape)
    if coords is None:
        return None

    x1, y1, x2, y2 = coords
    width = x2 - x1
    height = y2 - y1
    if width <= 0 or height <= 0:
        return None

    pad_x = int(round(width * (1.0 - inner_fraction) / 2.0))
    pad_y = int(round(height * (1.0 - inner_fraction) / 2.0))
    inner_x1 = min(x2 - 1, x1 + pad_x)
    inner_y1 = min(y2 - 1, y1 + pad_y)
    inner_x2 = max(inner_x1 + 1, x2 - pad_x)
    inner_y2 = max(inner_y1 + 1, y2 - pad_y)

    crop = frame[inner_y1:inner_y2, inner_x1:inner_x2]
    if crop.size == 0:
        return None
    return crop


def _dominant_rgb(crop: np.ndarray) -> Optional[np.ndarray]:
    if crop.ndim != 3 or crop.shape[2] < 3:
        return None

    rgb = crop[..., :3][:, :, ::-1].astype(np.float32) / 255.0
    flattened = rgb.reshape(-1, 3)
    if flattened.size == 0:
        return None

    channel_max = flattened.max(axis=1)
    channel_min = flattened.min(axis=1)
    delta = channel_max - channel_min
    saturation = np.divide(delta, np.maximum(channel_max, 1e-6))

    colorful = flattened[saturation >= 0.18]
    if len(colorful) >= max(10, len(flattened) // 8):
        return np.median(colorful, axis=0)
    return np.median(flattened, axis=0)


def _rgb_to_color_name(rgb: np.ndarray) -> Optional[str]:
    if rgb is None or len(rgb) < 3:
        return None

    r, g, b = [float(np.clip(value, 0.0, 1.0)) for value in rgb[:3]]
    maxc = max(r, g, b)
    minc = min(r, g, b)
    delta = maxc - minc

    if maxc < 0.12:
        return "black"

    saturation = 0.0 if maxc <= 1e-6 else delta / maxc
    if saturation < 0.12:
        if maxc > 0.85:
            return "white"
        return "gray"

    if maxc == r:
        hue = (g - b) / max(delta, 1e-6)
        hue = (hue % 6.0) * 60.0
    elif maxc == g:
        hue = ((b - r) / max(delta, 1e-6) + 2.0) * 60.0
    else:
        hue = ((r - g) / max(delta, 1e-6) + 4.0) * 60.0

    if maxc < 0.45 and 10.0 <= hue < 45.0:
        return "brown"
    if hue < 15.0 or hue >= 345.0:
        if maxc > 0.65 and saturation < 0.55:
            return "pink"
        return "red"
    if hue < 40.0:
        return "orange"
    if hue < 75.0:
        return "yellow"
    if hue < 170.0:
        return "green"
    if hue < 265.0:
        return "blue"
    if hue < 330.0:
        return "purple"
    return "red"


def estimate_detection_attributes(frame, bbox: BoundingBox) -> Dict[str, str]:
    """Estimate lightweight visual attributes for one detection from the current frame."""

    if frame is None or not isinstance(frame, np.ndarray):
        return {}
    if frame.ndim != 3 or frame.shape[2] < 3:
        return {}

    crop = _representative_crop(frame, bbox)
    if crop is None:
        return {}

    rgb = _dominant_rgb(crop)
    color_name = _rgb_to_color_name(rgb) if rgb is not None else None
    if not color_name:
        return {}
    return {"color": color_name}


def ultralytics_results_to_detections(results, frame=None) -> List[Detection]:
    """Convert Ultralytics tracking results into project `Detection` objects."""

    detections: List[Detection] = []
    for result in results:
        if getattr(result, "boxes", None) is None:
            continue

        ids = result.boxes.id
        for idx in range(len(result.boxes.cls)):
            class_id = int(result.boxes.cls[idx].item())
            label = result.names[class_id]
            confidence = float(result.boxes.conf[idx].item())
            xyxy = result.boxes.xyxy[idx].tolist()

            track_id = None
            if ids is not None:
                track_id = int(ids[idx].item())

            bbox = BoundingBox(
                x1=float(xyxy[0]),
                y1=float(xyxy[1]),
                x2=float(xyxy[2]),
                y2=float(xyxy[3]),
            )
            detections.append(
                Detection(
                    label=label,
                    confidence=confidence,
                    track_id=track_id,
                    bbox=bbox,
                    attributes=estimate_detection_attributes(frame, bbox),
                )
            )
    return detections


def _horizontal_region(center_x: float, frame_width: Optional[float]) -> str:
    width = float(frame_width or 640.0)
    if center_x < width / 3.0:
        return "left"
    if center_x > 2.0 * width / 3.0:
        return "right"
    return "center"


def build_scene_summary(
    detections: Sequence[Detection],
    max_items: int = 8,
    frame_width: Optional[float] = None,
) -> str:
    """Create a short textual summary of visible detections for grounding/debugging."""

    if not detections:
        return "No tracked objects are currently visible."

    parts = []
    for detection in detections[:max_items]:
        horizontal_region = _horizontal_region(detection.bbox.center_x, frame_width=frame_width)
        color = detection.attributes.get("color")
        description = f"{detection.label}"
        if detection.track_id is not None:
            description += f" id={detection.track_id}"
        description += f" conf={detection.confidence:.2f}"
        description += f" at {horizontal_region}"
        if color:
            description += f" color={color}"
        parts.append(description)

    return "; ".join(parts)


def top_labels(detections: Iterable[Detection]) -> List[str]:
    """Return unique labels in first-seen order."""

    seen = set()
    labels: List[str] = []
    for detection in detections:
        if detection.label not in seen:
            seen.add(detection.label)
            labels.append(detection.label)
    return labels
