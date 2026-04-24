#!/usr/bin/env python3
"""Track a spoken/text target using the pan/tilt camera inside a Gazebo world."""

from __future__ import annotations

import argparse
import math
import pathlib
import signal
import sys
import time
from typing import Optional

try:
    import ub_camera
except ImportError as exc:
    raise SystemExit(
        "Missing dependency. Install ub_code or make it importable before running: "
        f"{exc}"
    )

try:
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

from ie582_final_project.pan_tilt_controller import PanTiltControllerConfig
from ie582_final_project.pan_tilt_pipeline import PanTiltTargetingPipeline
from ie582_final_project.runtime_inputs import RuntimeCommandInputs
from ie582_final_project.vision import build_scene_summary, ultralytics_results_to_detections


DEFAULT_TOPIC = "/world/default/model/pantilt/link/tilt_link/sensor/camera/image"


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


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
        yolo_model_name: str,
        conf_threshold: float,
        rows: int,
        cols: int,
        fps: int,
        stream_port: int,
        protocol: str,
        no_stream: bool,
        pan_min_deg: float,
        pan_max_deg: float,
        tilt_min_deg: float,
        tilt_max_deg: float,
        horizontal_fov_deg: float,
        vertical_fov_deg: float,
    ) -> None:
        self.topic = topic
        self.gazebo_model_name = gazebo_model_name
        self.node = Node()
        self.yolo_model_name = yolo_model_name
        self.conf_threshold = conf_threshold
        self._shutdown = False

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

        self.camera = ub_camera.CameraGazebo(
            topic=self.topic,
            paramDict={
                "res_rows": rows,
                "res_cols": cols,
                "fps_target": fps,
                "outputPort": stream_port,
            },
        )
        self.camera.start(
            startStream=not no_stream,
            port=stream_port,
            protocol=protocol,
        )

        self.camera.addUltralytics(
            idName="track",
            model_name=self.yolo_model_name,
            conf_threshold=self.conf_threshold,
            postFunction=self._on_track_results,
            postFunctionArgs={},
            drawBox=True,
            drawLabel=True,
        )

        self._install_signal_handlers()

        if not no_stream:
            print(f"Stream URL: {self.camera.streamURL}")
        print(f"Subscribed to Gazebo topic: {self.topic}")
        print(f"Publishing pan/tilt commands for model: {self.gazebo_model_name}")

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
        msg = Double()
        msg.data = math.radians(angle_deg)

        if joint_name == "pan_joint":
            self.pan_pub.publish(msg)
        elif joint_name == "tilt_joint":
            self.tilt_pub.publish(msg)

        self.joint_state[joint_name]["angle_deg"] = angle_deg

    def _on_track_results(self, args_dict: dict) -> None:
        self._refresh_command_inputs()

        try:
            frame = self.camera.getFrameCopy()
        except Exception:
            frame = None

        detections = ultralytics_results_to_detections(args_dict["results"], frame=frame)
        if not detections:
            return

        cmd, best, _ = self.pipeline.step(
            detections=detections,
            frame_shape=(self.camera.res_rows, self.camera.res_cols),
            joint_state=self.joint_state,
            robot_id=None,
        )

        for joint_name, angle_deg in cmd.joint_targets.items():
            self._publish_joint_command(joint_name, angle_deg)

        if best is not None:
            print(
                f"target id={best.detection.track_id} label={best.detection.label} "
                f"score={best.total:.3f} cmd={cmd.joint_targets}"
            )
            print(f"[scene] {build_scene_summary(detections, frame_width=self.camera.res_cols)}")

    def run(self) -> None:
        while not self._shutdown:
            self._refresh_command_inputs()
            time.sleep(0.2)

    def shutdown(self) -> None:
        try:
            if "track" in self.camera.ultralytics:
                self.camera.ultralytics["track"].stop()
        except Exception:
            pass
        try:
            self.camera.shutdown()
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
    parser.add_argument("--model-name", default="yolo11n.pt", help="Ultralytics tracking model")
    parser.add_argument("--conf-threshold", type=float, default=0.65)
    parser.add_argument("--rows", type=int, default=480)
    parser.add_argument("--cols", type=int, default=640)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--stream-port", type=int, default=8000)
    parser.add_argument("--protocol", default="mjpeg", choices=("mjpeg", "websocket", "webrtc"))
    parser.add_argument("--no-stream", action="store_true")
    parser.add_argument("--pan-min-deg", type=float, default=-180.0)
    parser.add_argument("--pan-max-deg", type=float, default=180.0)
    parser.add_argument("--tilt-min-deg", type=float, default=-90.0)
    parser.add_argument("--tilt-max-deg", type=float, default=90.0)
    parser.add_argument("--horizontal-fov-deg", type=float, default=60.0)
    parser.add_argument("--vertical-fov-deg", type=float, default=46.8)
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
        yolo_model_name=args.model_name,
        conf_threshold=args.conf_threshold,
        rows=args.rows,
        cols=args.cols,
        fps=args.fps,
        stream_port=args.stream_port,
        protocol=args.protocol,
        no_stream=args.no_stream,
        pan_min_deg=args.pan_min_deg,
        pan_max_deg=args.pan_max_deg,
        tilt_min_deg=args.tilt_min_deg,
        tilt_max_deg=args.tilt_max_deg,
        horizontal_fov_deg=args.horizontal_fov_deg,
        vertical_fov_deg=args.vertical_fov_deg,
    )

    try:
        tracker.run()
    finally:
        tracker.shutdown()


if __name__ == "__main__":
    main()
