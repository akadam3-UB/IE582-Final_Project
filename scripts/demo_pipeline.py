#!/usr/bin/env python3
"""Small local demo for the command-grounded multi-target pipeline."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

# Allow running without installation: `python scripts/demo_pipeline.py`
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ie582_final_project.models import BoundingBox, Detection
from ie582_final_project.pipeline import MultiTargetPipeline


DEFAULT_COMMAND = "track the red cone"


def sample_detections() -> list[Detection]:
    return [
        Detection(
            label="cone",
            confidence=0.91,
            track_id=3,
            bbox=BoundingBox(260, 180, 360, 360),
            attributes={"color": "red"},
        ),
        Detection(
            label="person",
            confidence=0.88,
            track_id=7,
            bbox=BoundingBox(410, 140, 620, 430),
            attributes={"color": "blue"},
        ),
        Detection(
            label="cone",
            confidence=0.83,
            track_id=9,
            bbox=BoundingBox(60, 200, 150, 355),
            attributes={"color": "yellow"},
        ),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo multi-target prioritization pipeline.")
    parser.add_argument("--command", default=DEFAULT_COMMAND, help="User command text")
    parser.add_argument(
        "--vlm-json",
        default=None,
        help="Optional JSON text emitted by a VLM (e.g., '{\"action\":\"track\"}').",
    )
    parser.add_argument(
        "--obstacle-side",
        choices=["left", "right"],
        default=None,
        help="Optional obstacle hint for steering bias.",
    )
    args = parser.parse_args()

    pipeline = MultiTargetPipeline()

    vlm_text = None
    if args.vlm_json:
        # Accept either raw JSON or a JSON-serializable object string.
        parsed = json.loads(args.vlm_json)
        vlm_text = json.dumps(parsed)

    intent = pipeline.update_command(args.command, vlm_text=vlm_text)

    detections = sample_detections()
    frame_shape = (480, 640)
    drive, best, ranked = pipeline.step(
        detections=detections,
        frame_shape=frame_shape,
        obstacle_side=args.obstacle_side,
    )

    print("Intent:", intent)
    print()

    if best:
        print("Selected target:")
        print("  track_id:", best.detection.track_id)
        print("  label:", best.detection.label)
        print("  total score:", round(best.total, 4))
        print("  reason:", best.reason)
    else:
        print("Selected target: None")

    print()
    print("Drive command:", drive)
    print()

    print("Ranking:")
    for i, score in enumerate(ranked, start=1):
        det = score.detection
        print(
            f"  {i}. id={det.track_id} label={det.label} conf={det.confidence:.2f} "
            f"score={score.total:.4f}"
        )


if __name__ == "__main__":
    main()
