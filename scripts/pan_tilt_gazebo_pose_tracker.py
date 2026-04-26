#!/usr/bin/env python3
"""Simulation-first pan/tilt tracker using Gazebo ground-truth poses.

This is a stable fallback for the temporary test world on macOS, where the
Gazebo + Python 3.14 environment can run the simulator but Ultralytics / Torch
prediction is currently unstable. It still exercises command parsing, target
selection, target lock, and pan/tilt control end to end.
"""

from __future__ import annotations

import argparse
import math
import pathlib
import signal
import sys
import threading
import time
from typing import Dict, Iterable, List, Optional, Tuple

try:
    from gz.msgs10 import pose_v_pb2
    from gz.msgs10.double_pb2 import Double
    from gz.transport13 import Node
except ImportError as exc:
    raise SystemExit(
        "Missing Gazebo Python bindings. Install the Gazebo transport packages "
        "required by your class environment."
    ) from exc

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ie582_final_project.models import BoundingBox, Detection
from ie582_final_project.pan_tilt_controller import PanTiltControllerConfig
from ie582_final_project.pan_tilt_pipeline import PanTiltTargetingPipeline
from ie582_final_project.runtime_inputs import RuntimeCommandInputs
from ie582_final_project.vision import build_scene_summary


DEFAULT_POSE_TOPIC = "/world/default/pose/info"


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class GazeboPosePanTiltTracker:
    def __init__(
        self,
        pose_topic: str,
        gazebo_model_name: str,
        command_text: str,
        command_file: Optional[str],
        audio_file: Optional[str],
        vlm_json_file: Optional[str],
        whisper_model: str,
        whisper_backend: str,
        rows: int,
        cols: int,
        pan_min_deg: float,
        pan_max_deg: float,
        tilt_min_deg: float,
        tilt_max_deg: float,
        horizontal_fov_deg: float,
        vertical_fov_deg: float,
        tracked_prefixes: Iterable[str],
        base_pose_xyz: Tuple[float, float, float],
        tilt_joint_offset_m: float,
        sensor_forward_offset_m: float,
        human_height_m: float,
        human_width_m: float,
    ) -> None:
        self.pose_topic = pose_topic
        self.gazebo_model_name = gazebo_model_name
        self.node = Node()
        self._shutdown = False

        self.res_rows = int(rows)
        self.res_cols = int(cols)
        self.horizontal_fov_deg = float(horizontal_fov_deg)
        self.vertical_fov_deg = float(vertical_fov_deg)
        self.base_pose_xyz = tuple(float(v) for v in base_pose_xyz)
        self.tilt_joint_offset_m = float(tilt_joint_offset_m)
        self.sensor_forward_offset_m = float(sensor_forward_offset_m)
        self.human_height_m = float(human_height_m)
        self.human_width_m = float(human_width_m)
        self.tracked_prefixes = tuple(prefix.strip() for prefix in tracked_prefixes if prefix.strip())

        self._pose_lock = threading.Lock()
        self._latest_positions: Dict[str, Tuple[float, float, float]] = {}
        self._track_id_by_name: Dict[str, int] = {}
        self._next_track_id = 1
        self._last_scene_summary = ""

        self.command_inputs = RuntimeCommandInputs(
            initial_command=command_text,
            command_file=command_file,
            audio_file=audio_file,
            vlm_json_file=vlm_json_file,
            whisper_model=whisper_model,
            whisper_backend=whisper_backend,
        )

        controller_config = PanTiltControllerConfig(
            pan_joint_name="pan_joint",
            tilt_joint_name="tilt_joint",
            pan_fov_deg=horizontal_fov_deg,
            tilt_fov_deg=vertical_fov_deg,
        )
        self.pipeline = PanTiltTargetingPipeline(controller_config=controller_config)
        initial_command_text, initial_vlm_text, _ = self.command_inputs.poll()
        self.pipeline.update_command(initial_command_text, vlm_text=initial_vlm_text)

        self.joint_state = {
            "pan_joint": {
                "angle_deg": 0.0,
                "min_angle": pan_min_deg,
                "max_angle": pan_max_deg,
            },
            "tilt_joint": {
                "angle_deg": 0.0,
                "min_angle": tilt_min_deg,
                "max_angle": tilt_max_deg,
            },
        }

        self.pan_pub = self.node.advertise(
            f"/model/{self.gazebo_model_name}/joint/pan_joint/0/cmd_pos",
            Double,
        )
        self.tilt_pub = self.node.advertise(
            f"/model/{self.gazebo_model_name}/joint/tilt_joint/0/cmd_pos",
            Double,
        )

        self.node.subscribe(pose_v_pb2.Pose_V, self.pose_topic, self._on_pose_message)
        self._install_signal_handlers()

        print(f"Subscribed to Gazebo pose topic: {self.pose_topic}")
        print(f"Publishing pan/tilt commands for model: {self.gazebo_model_name}")

    def _install_signal_handlers(self) -> None:
        def handle_signal(signum, frame):
            self._shutdown = True

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

    def _on_pose_message(self, msg: pose_v_pb2.Pose_V) -> None:
        positions: Dict[str, Tuple[float, float, float]] = {}
        for pose in msg.pose:
            name = pose.name
            if not any(name.startswith(prefix) for prefix in self.tracked_prefixes):
                continue
            positions[name] = (
                float(pose.position.x),
                float(pose.position.y),
                float(pose.position.z),
            )

        with self._pose_lock:
            self._latest_positions = positions

    def _refresh_command_inputs(self) -> None:
        try:
            command_text, vlm_text, changed = self.command_inputs.poll()
        except RuntimeError as exc:
            print(f"[command-input] {exc}")
            return

        if not changed:
            return

        intent = self.pipeline.update_command(command_text, vlm_text=vlm_text)
        print(f"[command] {intent.raw_text or command_text} -> {intent}")

    def _publish_joint_command(self, joint_name: str, angle_deg: float) -> None:
        msg = Double()
        msg.data = math.radians(angle_deg)

        if joint_name == "pan_joint":
            self.pan_pub.publish(msg)
        elif joint_name == "tilt_joint":
            self.tilt_pub.publish(msg)

        self.joint_state[joint_name]["angle_deg"] = angle_deg

    def _camera_pose(self) -> Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]:
        pan_rad = math.radians(float(self.joint_state["pan_joint"]["angle_deg"]))
        tilt_down_rad = math.radians(float(self.joint_state["tilt_joint"]["angle_deg"]))

        cos_yaw = math.cos(pan_rad)
        sin_yaw = math.sin(pan_rad)
        cos_pitch = math.cos(tilt_down_rad)
        sin_pitch = math.sin(tilt_down_rad)

        forward = (
            cos_pitch * cos_yaw,
            cos_pitch * sin_yaw,
            -sin_pitch,
        )
        left = (-sin_yaw, cos_yaw, 0.0)
        up = (
            forward[1] * left[2] - forward[2] * left[1],
            forward[2] * left[0] - forward[0] * left[2],
            forward[0] * left[1] - forward[1] * left[0],
        )

        base_x, base_y, base_z = self.base_pose_xyz
        tilt_origin = (base_x, base_y, base_z + self.tilt_joint_offset_m)
        camera_origin = (
            tilt_origin[0] + self.sensor_forward_offset_m * forward[0],
            tilt_origin[1] + self.sensor_forward_offset_m * forward[1],
            tilt_origin[2] + self.sensor_forward_offset_m * forward[2],
        )
        return camera_origin, forward, left, up

    def _track_id_for_name(self, name: str) -> int:
        track_id = self._track_id_by_name.get(name)
        if track_id is not None:
            return track_id
        track_id = self._next_track_id
        self._next_track_id += 1
        self._track_id_by_name[name] = track_id
        return track_id

    def _project_entities_to_detections(self) -> List[Detection]:
        with self._pose_lock:
            positions = dict(self._latest_positions)

        if not positions:
            return []

        camera_origin, forward, left, up = self._camera_pose()
        hfov_rad = math.radians(self.horizontal_fov_deg)
        vfov_rad = math.radians(self.vertical_fov_deg)
        detections: List[Detection] = []

        for name, position in positions.items():
            rel = (
                position[0] - camera_origin[0],
                position[1] - camera_origin[1],
                position[2] - camera_origin[2],
            )
            x_forward = rel[0] * forward[0] + rel[1] * forward[1] + rel[2] * forward[2]
            y_left = rel[0] * left[0] + rel[1] * left[1] + rel[2] * left[2]
            z_up = rel[0] * up[0] + rel[1] * up[1] + rel[2] * up[2]

            if x_forward <= 0.05:
                continue

            yaw = math.atan2(y_left, x_forward)
            pitch = math.atan2(z_up, x_forward)
            if abs(yaw) > hfov_rad / 2.0 or abs(pitch) > vfov_rad / 2.0:
                continue

            center_x = self.res_cols / 2.0 - (yaw / (hfov_rad / 2.0)) * (self.res_cols / 2.0)
            center_y = self.res_rows / 2.0 - (pitch / (vfov_rad / 2.0)) * (self.res_rows / 2.0)

            height_angle = 2.0 * math.atan2(self.human_height_m / 2.0, x_forward)
            width_angle = 2.0 * math.atan2(self.human_width_m / 2.0, x_forward)
            bbox_h = max(20.0, (height_angle / max(vfov_rad, 1e-6)) * self.res_rows)
            bbox_w = max(10.0, (width_angle / max(hfov_rad, 1e-6)) * self.res_cols)

            x1 = _clamp(center_x - bbox_w / 2.0, 0.0, self.res_cols - 1.0)
            y1 = _clamp(center_y - bbox_h / 2.0, 0.0, self.res_rows - 1.0)
            x2 = _clamp(center_x + bbox_w / 2.0, x1 + 1.0, self.res_cols)
            y2 = _clamp(center_y + bbox_h / 2.0, y1 + 1.0, self.res_rows)

            detections.append(
                Detection(
                    label="person",
                    confidence=0.95,
                    track_id=self._track_id_for_name(name),
                    bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                    attributes={"source": "gazebo_pose", "entity_name": name},
                )
            )

        detections.sort(key=lambda det: det.track_id or 0)
        return detections

    def run(self) -> None:
        waiting_logged = False
        while not self._shutdown:
            self._refresh_command_inputs()
            detections = self._project_entities_to_detections()
            if not detections:
                if not waiting_logged:
                    print(f"Waiting for visible tracked entities on {self.pose_topic} ...")
                    waiting_logged = True
                time.sleep(0.05)
                continue

            waiting_logged = False
            cmd, best, _ = self.pipeline.step(
                detections=detections,
                frame_shape=(self.res_rows, self.res_cols),
                joint_state=self.joint_state,
                robot_id=None,
            )

            for joint_name, angle_deg in cmd.joint_targets.items():
                self._publish_joint_command(joint_name, angle_deg)

            scene_summary = build_scene_summary(detections, frame_width=self.res_cols)
            if best is not None:
                entity_name = best.detection.attributes.get("entity_name", "")
                print(
                    f"target id={best.detection.track_id} label={best.detection.label} "
                    f"entity={entity_name} score={best.total:.3f} cmd={cmd.joint_targets}"
                )
            if scene_summary != self._last_scene_summary:
                print(f"[scene] {scene_summary}")
                self._last_scene_summary = scene_summary
            time.sleep(0.05)

    def shutdown(self) -> None:
        try:
            self.node.unsubscribe(self.pose_topic)
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Gazebo pose-based pan/tilt tracker")
    parser.add_argument("--pose-topic", default=DEFAULT_POSE_TOPIC, help="Gazebo pose info topic")
    parser.add_argument("--gazebo-model-name", default="pantilt", help="Gazebo model name containing pan_joint and tilt_joint")
    parser.add_argument("--command", default="track the person", help="Initial command text")
    parser.add_argument("--command-file", default=None, help="Optional text file to poll for command updates")
    parser.add_argument("--audio-file", default=None, help="Optional audio file to transcribe when updated")
    parser.add_argument("--vlm-json-file", default=None, help="Optional file containing VLM JSON grounding output")
    parser.add_argument("--whisper-model", default="base", help="Whisper model name for audio-file transcription")
    parser.add_argument("--whisper-backend", default="auto", choices=("auto", "mlx-whisper", "whisper"), help="Speech backend preference")
    parser.add_argument("--rows", type=int, default=480)
    parser.add_argument("--cols", type=int, default=640)
    parser.add_argument("--pan-min-deg", type=float, default=-180.0)
    parser.add_argument("--pan-max-deg", type=float, default=180.0)
    parser.add_argument("--tilt-min-deg", type=float, default=-68.0)
    parser.add_argument("--tilt-max-deg", type=float, default=68.0)
    parser.add_argument("--horizontal-fov-deg", type=float, default=60.0)
    parser.add_argument("--vertical-fov-deg", type=float, default=46.8)
    parser.add_argument("--tracked-prefix", action="append", default=["person"], help="Entity-name prefix to treat as a visible person target")
    parser.add_argument("--base-x", type=float, default=0.0)
    parser.add_argument("--base-y", type=float, default=0.0)
    parser.add_argument("--base-z", type=float, default=1.45)
    parser.add_argument("--tilt-joint-offset-m", type=float, default=0.22)
    parser.add_argument("--sensor-forward-offset-m", type=float, default=0.18)
    parser.add_argument("--human-height-m", type=float, default=1.7)
    parser.add_argument("--human-width-m", type=float, default=0.55)
    args = parser.parse_args()

    tracker = GazeboPosePanTiltTracker(
        pose_topic=args.pose_topic,
        gazebo_model_name=args.gazebo_model_name,
        command_text=args.command,
        command_file=args.command_file,
        audio_file=args.audio_file,
        vlm_json_file=args.vlm_json_file,
        whisper_model=args.whisper_model,
        whisper_backend=args.whisper_backend,
        rows=args.rows,
        cols=args.cols,
        pan_min_deg=args.pan_min_deg,
        pan_max_deg=args.pan_max_deg,
        tilt_min_deg=args.tilt_min_deg,
        tilt_max_deg=args.tilt_max_deg,
        horizontal_fov_deg=args.horizontal_fov_deg,
        vertical_fov_deg=args.vertical_fov_deg,
        tracked_prefixes=args.tracked_prefix,
        base_pose_xyz=(args.base_x, args.base_y, args.base_z),
        tilt_joint_offset_m=args.tilt_joint_offset_m,
        sensor_forward_offset_m=args.sensor_forward_offset_m,
        human_height_m=args.human_height_m,
        human_width_m=args.human_width_m,
    )

    try:
        tracker.run()
    finally:
        tracker.shutdown()


if __name__ == "__main__":
    main()
