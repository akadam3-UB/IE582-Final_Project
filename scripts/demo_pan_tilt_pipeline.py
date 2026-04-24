#!/usr/bin/env python3
"""Demo: command-grounded target selection for pan/tilt camera control."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ie582_final_project.models import BoundingBox, Detection
from ie582_final_project.pan_tilt_pipeline import PanTiltTargetingPipeline


def sample_detections() -> list[Detection]:
    return [
        Detection(
            label="person",
            confidence=0.93,
            track_id=21,
            bbox=BoundingBox(70, 80, 270, 430),
            attributes={"color": "blue"},
        ),
        Detection(
            label="cone",
            confidence=0.89,
            track_id=8,
            bbox=BoundingBox(330, 170, 420, 350),
            attributes={"color": "red"},
        ),
    ]


def sample_joint_state() -> dict:
    # Shape matches host `status` payload in the class repo.
    return {
        "arm_shoulder_pan_joint": {
            "angle_deg": 57.0,
            "min_angle": 0.0,
            "max_angle": 114.0,
            "OK": True,
            "torque": True,
        },
        "arm_shoulder_lift_joint": {
            "angle_deg": 125.0,
            "min_angle": 45.0,
            "max_angle": 160.0,
            "OK": True,
            "torque": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Pan/tilt targeting demo")
    parser.add_argument("--command", default="track the blue person")
    parser.add_argument("--robot-id", type=int, default=1)
    parser.add_argument(
        "--vlm-json",
        default=None,
        help="Optional VLM JSON string with action/target fields.",
    )
    args = parser.parse_args()

    pipeline = PanTiltTargetingPipeline()

    vlm_text = None
    if args.vlm_json:
        parsed = json.loads(args.vlm_json)
        vlm_text = json.dumps(parsed)

    intent = pipeline.update_command(args.command, vlm_text=vlm_text)
    cmd, best, ranked = pipeline.step(
        detections=sample_detections(),
        frame_shape=(480, 640),
        joint_state=sample_joint_state(),
        robot_id=args.robot_id,
    )

    print("Intent:", intent)
    print()

    if best:
        print("Selected target:", {
            "track_id": best.detection.track_id,
            "label": best.detection.label,
            "score": round(best.total, 4),
            "reason": best.reason,
        })
    else:
        print("Selected target: None")

    print()
    print("PanTiltCommand:", cmd)
    print("Host command payload:", cmd.to_host_payload())
    print()

    print("Ranking:")
    for idx, score in enumerate(ranked, start=1):
        det = score.detection
        print(
            f"  {idx}. id={det.track_id} label={det.label} conf={det.confidence:.2f} "
            f"score={score.total:.4f}"
        )


if __name__ == "__main__":
    main()
