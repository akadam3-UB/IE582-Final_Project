#!/usr/bin/env python3
"""Track a spoken/text target using the pan/tilt camera inside a Gazebo world."""

from __future__ import annotations

import argparse
import math
import os
import pathlib
import signal
import sys
import threading
import time
from typing import Optional, Tuple

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np

try:
    from gz.msgs10 import image_pb2
    from gz.msgs10.boolean_pb2 import Boolean
    from gz.msgs10.double_pb2 import Double
    from gz.msgs10.pose_pb2 import Pose
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

from ie582_final_project.pan_tilt_controller import PanTiltControllerConfig
from ie582_final_project.pan_tilt_pipeline import PanTiltTargetingPipeline
from ie582_final_project.runtime_inputs import RuntimeCommandInputs
from ie582_final_project.vision import (
    build_scene_summary,
    color_proxy_detections,
    ultralytics_results_to_detections,
)


DEFAULT_TOPIC = "/world/room_427_tracking_test/model/pantilt/link/tilt_link/sensor/camera/image"

_PIXEL_FORMAT_CHANNELS = {
    image_pb2.L_INT8: 1,
    image_pb2.RGB_INT8: 3,
    image_pb2.RGBA_INT8: 4,
    image_pb2.BGRA_INT8: 4,
    image_pb2.BGR_INT8: 3,
}


class GazeboPanTiltTracker:
    def __init__(
        self,
        topic: str,
        gazebo_model_name: str,
        command_text: str,
        command_file: Optional[str],
        audio_file: Optional[str],
        vlm_json_file: Optional[str],
        whisper_model: str,
        whisper_backend: str,
        detector: str,
        yolo_model_name: str,
        conf_threshold: float,
        rows: int,
        cols: int,
        fps: int,
        stream_port: int,
        protocol: str,
        no_stream: bool,
        control_mode: str,
        world_name: str,
        model_pose_x: float,
        model_pose_y: float,
        model_pose_z: float,
        model_base_yaw_deg: float,
        pose_timeout_ms: int,
        pan_min_deg: float,
        pan_max_deg: float,
        tilt_min_deg: float,
        tilt_max_deg: float,
        horizontal_fov_deg: float,
        vertical_fov_deg: float,
        pan_deadband_px: float,
        tilt_deadband_px: float,
        tilt_setpoint_y_fraction: float,
        gain_scale: float,
        max_step_deg: float,
        control_rate_hz: float,
        invert_pan: bool,
        initial_pan_deg: float,
        initial_tilt_deg: float,
        lock_tilt: bool,
    ) -> None:
        self.topic = topic
        self.gazebo_model_name = gazebo_model_name
        self.node = Node()
        self.detector = detector
        self.yolo_model_name = yolo_model_name
        self.conf_threshold = conf_threshold
        self._shutdown = False
        self.initial_pan_deg = float(initial_pan_deg)
        self.initial_tilt_deg = float(initial_tilt_deg)
        self.invert_pan = bool(invert_pan)
        self.lock_tilt = bool(lock_tilt)

        self.res_rows = rows
        self.res_cols = cols
        self.fps = fps
        self.stream_port = stream_port
        self.protocol = protocol
        self.no_stream = no_stream
        self.control_mode = control_mode
        self.pose_service = f"/world/{world_name}/set_pose"
        self.model_pose_xyz = (
            float(model_pose_x),
            float(model_pose_y),
            float(model_pose_z),
        )
        self.model_base_yaw_deg = float(model_base_yaw_deg)
        self.pose_timeout_ms = int(pose_timeout_ms)
        self.control_interval_s = 1.0 / max(float(control_rate_hz), 0.1)

        self._frame_lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_frame_index = 0
        self._processed_frame_index = 0
        self._last_control_time = 0.0
        self._received_frame = False
        self._warned_formats: set[int] = set()
        self._last_scene_summary = ""
        self._last_target_log_time = 0.0
        self._last_target_key: Optional[Tuple[Optional[int], str]] = None
        self._last_hold_log_time = 0.0

        self.command_inputs = RuntimeCommandInputs(
            initial_command=command_text,
            command_file=command_file,
            audio_file=audio_file,
            vlm_json_file=vlm_json_file,
            whisper_model=whisper_model,
            whisper_backend=whisper_backend,
        )

        pan_fov_deg = -horizontal_fov_deg if self.invert_pan else horizontal_fov_deg
        controller_config = PanTiltControllerConfig(
            pan_joint_name="pan_joint",
            tilt_joint_name="tilt_joint",
            pan_fov_deg=pan_fov_deg,
            tilt_fov_deg=vertical_fov_deg,
            pan_deadband_px=pan_deadband_px,
            tilt_deadband_px=tilt_deadband_px,
            tilt_setpoint_y_fraction=tilt_setpoint_y_fraction,
            gain_scale=gain_scale,
            max_step_deg=max_step_deg,
        )
        self.pipeline = PanTiltTargetingPipeline(controller_config=controller_config)
        initial_command_text, initial_vlm_text, _ = self.command_inputs.poll()
        self.pipeline.update_command(initial_command_text, vlm_text=initial_vlm_text)

        self.joint_state = {
            "pan_joint": {
                "angle_deg": self.initial_pan_deg,
                "min_angle": pan_min_deg,
                "max_angle": pan_max_deg,
            },
            "tilt_joint": {
                "angle_deg": self.initial_tilt_deg,
                "min_angle": tilt_min_deg,
                "max_angle": tilt_max_deg,
            },
        }

        self.pan_pubs = [
            self.node.advertise(topic, Double)
            for topic in (
                f"/model/{self.gazebo_model_name}/joint/pan_joint/cmd_pos",
                f"/model/{self.gazebo_model_name}/joint/pan_joint/0/cmd_pos",
            )
        ]
        self.tilt_pubs = [
            self.node.advertise(topic, Double)
            for topic in (
                f"/model/{self.gazebo_model_name}/joint/tilt_joint/cmd_pos",
                f"/model/{self.gazebo_model_name}/joint/tilt_joint/0/cmd_pos",
            )
        ]

        self.model = self._load_yolo_model() if self.detector == "yolo" else None
        self.node.subscribe(image_pb2.Image, self.topic, self._on_image_message)
        self._install_signal_handlers()
        self._publish_joint_command("pan_joint", self.initial_pan_deg)
        if not self.lock_tilt:
            self._publish_joint_command("tilt_joint", self.initial_tilt_deg)

        if not self.no_stream:
            print(
                "Note: direct Gazebo mode processes frames internally and does not "
                "rebroadcast an MJPEG/WebSocket stream."
            )
        print(f"Subscribed to Gazebo topic: {self.topic}")
        print(f"Publishing pan/tilt commands for model: {self.gazebo_model_name}")
        print(f"Pan control mode: {self.control_mode}")
        if self.control_mode == "pose":
            print(f"Pose control service: {self.pose_service}")
        print(f"Detector mode: {self.detector}")
        if self.invert_pan:
            print("Pan direction inverted for the Gazebo pantilt model.")
        if self.lock_tilt:
            print("Tilt is fixed by the Gazebo model for a stable camera POV.")

    def _load_yolo_model(self):
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise SystemExit(
                "Missing Ultralytics. Install optional vision dependencies with "
                "`python3 -m pip install -e \".[vision]\"`, or run the default "
                "`--detector color-proxy` mode."
            ) from exc
        return YOLO(self.yolo_model_name)

    def _set_model_pose(self, pan_deg: Optional[float] = None, tilt_deg: Optional[float] = None) -> None:
        pose = Pose()
        pose.name = self.gazebo_model_name
        pose.position.x, pose.position.y, pose.position.z = self.model_pose_xyz

        pan_angle = self.joint_state["pan_joint"]["angle_deg"] if pan_deg is None else pan_deg
        tilt_angle = self.joint_state["tilt_joint"]["angle_deg"] if tilt_deg is None else tilt_deg

        yaw_rad = math.radians(self.model_base_yaw_deg + pan_angle)
        pitch_rad = math.radians(tilt_angle)
        cy = math.cos(yaw_rad * 0.5)
        sy = math.sin(yaw_rad * 0.5)
        cp = math.cos(pitch_rad * 0.5)
        sp = math.sin(pitch_rad * 0.5)

        pose.orientation.w = cy * cp
        pose.orientation.x = -sy * sp
        pose.orientation.y = cy * sp
        pose.orientation.z = sy * cp

        try:
            self.node.request(
                self.pose_service,
                pose,
                Pose,
                Boolean,
                self.pose_timeout_ms,
            )
        except Exception as exc:
            now = time.monotonic()
            if now - self._last_hold_log_time >= 2.0:
                print(f"[pose-control] set_pose failed: {exc}")
                self._last_hold_log_time = now

    def _install_signal_handlers(self) -> None:
        def handle_signal(signum, frame):
            self._shutdown = True

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

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
        if self.control_mode == "pose" and joint_name in {"pan_joint", "tilt_joint"}:
            if joint_name == "pan_joint":
                self._set_model_pose(pan_deg=angle_deg)
            else:
                self._set_model_pose(tilt_deg=angle_deg)
            self.joint_state[joint_name]["angle_deg"] = angle_deg
            return

        msg = Double()
        msg.data = math.radians(angle_deg)

        if joint_name == "pan_joint":
            for publisher in self.pan_pubs:
                publisher.publish(msg)
        elif joint_name == "tilt_joint":
            for publisher in self.tilt_pubs:
                publisher.publish(msg)

        self.joint_state[joint_name]["angle_deg"] = angle_deg

    def _decode_image_message(self, msg: image_pb2.Image) -> Optional[np.ndarray]:
        width = int(msg.width)
        height = int(msg.height)
        pixel_format = int(msg.pixel_format_type)
        channels = _PIXEL_FORMAT_CHANNELS.get(pixel_format)
        if width <= 0 or height <= 0 or channels is None:
            if pixel_format not in self._warned_formats:
                self._warned_formats.add(pixel_format)
                print(
                    f"[camera] Unsupported Gazebo pixel format {pixel_format}; "
                    "expected RGB/BGR/RGBA/BGRA/L_INT8."
                )
            return None

        row_bytes = int(msg.step) if int(msg.step) > 0 else width * channels
        raw = np.frombuffer(msg.data, dtype=np.uint8)
        if raw.size < height * row_bytes:
            return None

        rows = raw[: height * row_bytes].reshape(height, row_bytes)
        packed = rows[:, : width * channels]

        if pixel_format == image_pb2.L_INT8:
            gray = packed.reshape(height, width).copy()
            return np.repeat(gray[:, :, None], 3, axis=2)

        frame = packed.reshape(height, width, channels)
        if pixel_format == image_pb2.RGB_INT8:
            return frame[:, :, ::-1].copy()
        if pixel_format == image_pb2.BGR_INT8:
            return frame.copy()
        if pixel_format == image_pb2.RGBA_INT8:
            return frame[:, :, [2, 1, 0]].copy()
        if pixel_format == image_pb2.BGRA_INT8:
            return frame[:, :, :3].copy()
        return None

    def _on_image_message(self, msg: image_pb2.Image) -> None:
        frame = self._decode_image_message(msg)
        if frame is None:
            return

        with self._frame_lock:
            self._latest_frame = frame
            self._latest_frame_index += 1
            self.res_rows, self.res_cols = frame.shape[:2]
            self._received_frame = True

    def _get_latest_frame(self) -> Tuple[Optional[np.ndarray], int]:
        with self._frame_lock:
            if self._latest_frame is None:
                return None, self._latest_frame_index
            return self._latest_frame.copy(), self._latest_frame_index

    def _process_latest_frame(self) -> bool:
        frame, frame_index = self._get_latest_frame()
        if frame is None or frame_index == self._processed_frame_index:
            return False
        now = time.monotonic()
        if now - self._last_control_time < self.control_interval_s:
            return False

        self._processed_frame_index = frame_index
        self._last_control_time = now
        if self.detector == "color-proxy":
            detections = color_proxy_detections(frame)
        else:
            try:
                results = self.model.track(
                    source=frame,
                    conf=self.conf_threshold,
                    persist=True,
                    verbose=False,
                )
            except Exception as exc:
                print(f"[tracking] Ultralytics inference failed: {exc}")
                time.sleep(0.5)
                return False
            detections = ultralytics_results_to_detections(results, frame=frame)

        if not detections:
            return True

        cmd, best, _ = self.pipeline.step(
            detections=detections,
            frame_shape=frame.shape[:2],
            joint_state=self.joint_state,
            robot_id=None,
        )

        joint_targets = dict(cmd.joint_targets)
        if self.lock_tilt:
            joint_targets.pop("tilt_joint", None)
        joint_targets = {
            joint_name: angle_deg
            for joint_name, angle_deg in joint_targets.items()
            if abs(angle_deg - self.joint_state[joint_name]["angle_deg"]) >= 1e-3
        }

        for joint_name, angle_deg in joint_targets.items():
            self._publish_joint_command(joint_name, angle_deg)

        scene_summary = build_scene_summary(detections, frame_width=frame.shape[1])
        if best is not None:
            self._last_hold_log_time = 0.0
            now = time.monotonic()
            target_key = (best.detection.track_id, best.detection.label)
            should_log_target = (
                target_key != self._last_target_key
                or now - self._last_target_log_time >= 1.0
            )
            if should_log_target:
                self._last_target_log_time = now
                self._last_target_key = target_key
                print(
                    f"target id={best.detection.track_id} label={best.detection.label} "
                    f"score={best.total:.3f} cmd={joint_targets}"
                )
        else:
            now = time.monotonic()
            if now - self._last_hold_log_time >= 2.0:
                print("[tracking] Requested target not visible; holding camera.")
                self._last_hold_log_time = now
        if scene_summary != self._last_scene_summary:
            print(f"[scene] {scene_summary}")
            self._last_scene_summary = scene_summary
        return True

    def run(self) -> None:
        waiting_logged = False
        while not self._shutdown:
            self._refresh_command_inputs()
            processed = self._process_latest_frame()
            if processed:
                waiting_logged = False
                continue

            if not self._received_frame and not waiting_logged:
                print(f"Waiting for frames on {self.topic} ...")
                waiting_logged = True
            time.sleep(0.05)

    def shutdown(self) -> None:
        try:
            self.node.unsubscribe(self.topic)
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Gazebo pan/tilt classroom tracker")
    parser.add_argument("--topic", default=DEFAULT_TOPIC, help="Gazebo camera image topic")
    parser.add_argument("--gazebo-model-name", default="pantilt", help="Gazebo model name containing pan_joint and tilt_joint")
    parser.add_argument("--command", default="track the person", help="Initial command text")
    parser.add_argument("--command-file", default=None, help="Optional text file to poll for command updates")
    parser.add_argument("--audio-file", default=None, help="Optional audio file to transcribe when updated")
    parser.add_argument("--vlm-json-file", default=None, help="Optional file containing VLM JSON grounding output")
    parser.add_argument("--whisper-model", default="base", help="Whisper model name for audio-file transcription")
    parser.add_argument("--whisper-backend", default="auto", choices=("auto", "mlx-whisper", "whisper"), help="Speech backend preference")
    parser.add_argument("--detector", default="color-proxy", choices=("color-proxy", "yolo"), help="Detection backend for Gazebo camera frames")
    parser.add_argument("--model-name", default="yolo11n.pt", help="Ultralytics tracking model")
    parser.add_argument("--conf-threshold", type=float, default=0.65)
    parser.add_argument("--rows", type=int, default=480)
    parser.add_argument("--cols", type=int, default=640)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--stream-port", type=int, default=8000)
    parser.add_argument("--protocol", default="mjpeg", choices=("mjpeg", "websocket", "webrtc"))
    parser.add_argument("--no-stream", action="store_true")
    parser.add_argument("--control-mode", default="pose", choices=("pose", "joint"), help="Use set_pose model yaw control or Gazebo joint-position control")
    parser.add_argument("--world-name", default="room_427_tracking_test", help="Gazebo world name for pose control")
    parser.add_argument("--model-pose-x", type=float, default=12.1, help="World X position for pose-control mode")
    parser.add_argument("--model-pose-y", type=float, default=3.27, help="World Y position for pose-control mode")
    parser.add_argument("--model-pose-z", type=float, default=2.35, help="World Z position for pose-control mode")
    parser.add_argument("--model-base-yaw-deg", type=float, default=180.0, help="Zero-pan model yaw for pose-control mode")
    parser.add_argument("--pose-timeout-ms", type=int, default=100, help="set_pose service timeout in milliseconds")
    parser.add_argument("--pan-min-deg", type=float, default=-180.0)
    parser.add_argument("--pan-max-deg", type=float, default=180.0)
    parser.add_argument("--tilt-min-deg", type=float, default=-90.0)
    parser.add_argument("--tilt-max-deg", type=float, default=90.0)
    parser.add_argument("--horizontal-fov-deg", type=float, default=60.0)
    parser.add_argument("--vertical-fov-deg", type=float, default=46.8)
    parser.add_argument("--pan-deadband-px", type=float, default=28.0, help="Ignore small horizontal image error to reduce Gazebo demo jitter")
    parser.add_argument("--tilt-deadband-px", type=float, default=40.0, help="Ignore small vertical image error")
    parser.add_argument("--tilt-setpoint-y-fraction", type=float, default=0.5, help="Desired vertical target location as a fraction of image height")
    parser.add_argument("--gain-scale", type=float, default=0.45, help="Camera tracker controller gain scale")
    parser.add_argument("--max-step-deg", type=float, default=1.5, help="Maximum joint step per processed frame")
    parser.add_argument("--control-rate-hz", type=float, default=4.0, help="Maximum visual-servo control updates per second")
    parser.add_argument("--invert-pan", dest="invert_pan", action="store_true", default=False, help="Invert horizontal image error for a reversed pan convention")
    parser.add_argument("--no-invert-pan", dest="invert_pan", action="store_false", help="Disable Gazebo pan direction inversion")
    parser.add_argument("--initial-pan-deg", type=float, default=0.0, help="Initial pan command for the included pantilt model")
    parser.add_argument("--initial-tilt-deg", type=float, default=25.0, help="Initial downward tilt command for the included pantilt model")
    parser.add_argument("--lock-tilt", action="store_true", help="Hold initial tilt and only track horizontally")
    args = parser.parse_args()

    tracker = GazeboPanTiltTracker(
        topic=args.topic,
        gazebo_model_name=args.gazebo_model_name,
        command_text=args.command,
        command_file=args.command_file,
        audio_file=args.audio_file,
        vlm_json_file=args.vlm_json_file,
        whisper_model=args.whisper_model,
        whisper_backend=args.whisper_backend,
        detector=args.detector,
        yolo_model_name=args.model_name,
        conf_threshold=args.conf_threshold,
        rows=args.rows,
        cols=args.cols,
        fps=args.fps,
        stream_port=args.stream_port,
        protocol=args.protocol,
        no_stream=args.no_stream,
        control_mode=args.control_mode,
        world_name=args.world_name,
        model_pose_x=args.model_pose_x,
        model_pose_y=args.model_pose_y,
        model_pose_z=args.model_pose_z,
        model_base_yaw_deg=args.model_base_yaw_deg,
        pose_timeout_ms=args.pose_timeout_ms,
        pan_min_deg=args.pan_min_deg,
        pan_max_deg=args.pan_max_deg,
        tilt_min_deg=args.tilt_min_deg,
        tilt_max_deg=args.tilt_max_deg,
        horizontal_fov_deg=args.horizontal_fov_deg,
        vertical_fov_deg=args.vertical_fov_deg,
        pan_deadband_px=args.pan_deadband_px,
        tilt_deadband_px=args.tilt_deadband_px,
        tilt_setpoint_y_fraction=args.tilt_setpoint_y_fraction,
        gain_scale=args.gain_scale,
        max_step_deg=args.max_step_deg,
        control_rate_hz=args.control_rate_hz,
        invert_pan=args.invert_pan,
        initial_pan_deg=args.initial_pan_deg,
        initial_tilt_deg=args.initial_tilt_deg,
        lock_tilt=args.lock_tilt,
    )

    try:
        tracker.run()
    finally:
        tracker.shutdown()


if __name__ == "__main__":
    main()
