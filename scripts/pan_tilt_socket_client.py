#!/usr/bin/env python3
"""Pan/tilt tracking client using class host socket protocol.

This script follows the event format documented in spring2026/socket_demo:
- host -> client: sessionstart, status, notice
- client -> host: userreq, command

It opens the session camera stream, runs Ultralytics tracking via ub_camera,
selects a command-grounded target, and emits pan/tilt joint commands.
"""

from __future__ import annotations

import argparse
import pathlib
import signal
import sys
import time
from typing import Dict, Optional

try:
    import socketio
    import ub_camera
    import ub_utils
except ImportError as exc:
    raise SystemExit(
        "Missing dependency. Install socketio + ub_code environment before running: "
        f"{exc}"
    )

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ie582_final_project.pan_tilt_pipeline import PanTiltTargetingPipeline
from ie582_final_project.runtime_inputs import RuntimeCommandInputs
from ie582_final_project.vision import build_scene_summary, ultralytics_results_to_detections


class PanTiltSocketClient:
    def __init__(
        self,
        host_url: str,
        command_text: str,
        command_file: Optional[str],
        audio_file: Optional[str],
        vlm_json_file: Optional[str],
        whisper_model: str,
        whisper_backend: str,
        robot_id: int,
        model_name: str,
        conf_threshold: float,
    ) -> None:
        self.host_url = host_url
        self.robot_id_request = robot_id
        self.model_name = model_name
        self.conf_threshold = conf_threshold

        self.pipeline = PanTiltTargetingPipeline()
        self.command_inputs = RuntimeCommandInputs(
            initial_command=command_text,
            command_file=command_file,
            audio_file=audio_file,
            vlm_json_file=vlm_json_file,
            whisper_model=whisper_model,
            whisper_backend=whisper_backend,
        )
        initial_command_text, initial_vlm_text, _ = self.command_inputs.poll()
        self.pipeline.update_command(initial_command_text, vlm_text=initial_vlm_text)

        self.sio = socketio.Client(ssl_verify=False)
        self.camera: Dict[str, object] = {}
        self.joint_state: Dict[str, object] = {}
        self.robot_id_active: Optional[int] = None

        self._shutdown = False
        self._install_signal_handlers()
        self._register_handlers()

    def _install_signal_handlers(self) -> None:
        def handle_signal(signum, frame):
            self._shutdown = True
            self.shutdown()

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

    def _register_handlers(self) -> None:
        @self.sio.event
        def connect() -> None:
            print("Connected to host:", self.host_url)
            self.sio.emit("userreq", ["join", self.robot_id_request])
            print(f"Requested queue join for robot {self.robot_id_request}")

        @self.sio.event
        def disconnect() -> None:
            print("Disconnected from host")

        @self.sio.on("notice")
        def on_notice(data) -> None:
            print("[notice]", data)

        @self.sio.on("sysinfo")
        def on_sysinfo(data) -> None:
            # Useful for debugging queue behavior.
            print("[sysinfo]", data)

        @self.sio.on("sessionstart")
        def on_sessionstart(data) -> None:
            print("[sessionstart]", data)
            robot_id = int(data["robotID"])
            self.robot_id_active = robot_id
            self.joint_state = data.get("joints", {})

            cam_id = f"session_robot_{robot_id}"
            camera_url = data.get("cameraURL")
            if not camera_url:
                print("sessionstart missing cameraURL; cannot start tracking")
                return

            if cam_id in self.camera:
                return

            self._start_camera(cam_id=cam_id, device=camera_url, intrinsics=data.get("intrinsics"))

            self.camera[cam_id].addUltralytics(
                idName="track",
                model_name=self.model_name,
                conf_threshold=self.conf_threshold,
                postFunction=self._on_track_results,
                postFunctionArgs={"camID": cam_id},
                drawBox=True,
                drawLabel=True,
            )
            print(f"Tracking started on {cam_id}")

        @self.sio.on("status")
        def on_status(data) -> None:
            # Payload: [robotID, jointStateDict]
            if not isinstance(data, list) or len(data) != 2:
                return
            robot_id, joints = data
            if self.robot_id_active is None:
                return
            if int(robot_id) != int(self.robot_id_active):
                return
            self.joint_state = joints

    def _start_camera(self, cam_id: str, device: str, intrinsics: Optional[dict]) -> None:
        port = ub_utils.findOpenPort(8000, options=range(8000, 8011))
        param_dict = {"res_rows": 480, "res_cols": 640, "fps_target": 30, "outputPort": port}

        self.camera[cam_id] = ub_camera.CameraUSB(paramDict=param_dict, device=device)
        self.camera[cam_id].start(startStream=False, port=port)

        if intrinsics:
            self.camera[cam_id].intrinsics = intrinsics
            self.camera[cam_id].intrinsics = self.camera[cam_id]._getIntrinsics()

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

    def _on_track_results(self, args_dict: dict) -> None:
        if self.robot_id_active is None:
            return

        self._refresh_command_inputs()

        cam_id = args_dict["camID"]
        results = args_dict["results"]
        cam = self.camera[cam_id]

        try:
            frame = cam.getFrameCopy()
        except Exception:
            frame = None

        detections = ultralytics_results_to_detections(results, frame=frame)
        if not detections:
            return

        frame_shape = (cam.res_rows, cam.res_cols)

        cmd, best, _ = self.pipeline.step(
            detections=detections,
            frame_shape=frame_shape,
            joint_state=self.joint_state,
            robot_id=self.robot_id_active,
        )

        payload = cmd.to_host_payload()
        if payload is not None:
            self.sio.emit("command", payload)

        if best is not None:
            print(
                f"target id={best.detection.track_id} label={best.detection.label} "
                f"score={best.total:.3f} cmd={cmd.joint_targets}"
            )
            print(f"[scene] {build_scene_summary(detections, frame_width=cam.res_cols)}")

    def run(self) -> None:
        self.sio.connect(f"{self.host_url}?role=user", transports=["websocket"])
        while not self._shutdown:
            self._refresh_command_inputs()
            time.sleep(0.2)

    def shutdown(self) -> None:
        for cam_id, cam in list(self.camera.items()):
            try:
                if "track" in cam.ultralytics:
                    cam.ultralytics["track"].stop()
            except Exception:
                pass
            try:
                cam.stop()
            except Exception:
                pass
            self.camera.pop(cam_id, None)

        try:
            self.sio.disconnect()
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Pan/tilt tracking client")
    parser.add_argument("--host-url", required=True, help="e.g. https://10.83.11.58:8085")
    parser.add_argument("--command", default="track the person", help="targeting command")
    parser.add_argument("--command-file", default=None, help="Optional text file to poll for command updates")
    parser.add_argument("--audio-file", default=None, help="Optional audio file to transcribe with Whisper when updated")
    parser.add_argument("--vlm-json-file", default=None, help="Optional file containing VLM JSON grounding output")
    parser.add_argument("--whisper-model", default="base", help="Whisper model name for audio-file transcription")
    parser.add_argument("--whisper-backend", default="auto", choices=("auto", "mlx-whisper", "whisper"), help="Speech backend preference")
    parser.add_argument("--robot-id", type=int, default=1, help="robot queue ID to join")
    parser.add_argument("--model-name", default="yolo11n.pt", help="Ultralytics model name")
    parser.add_argument("--conf-threshold", type=float, default=0.65)
    args = parser.parse_args()

    client = PanTiltSocketClient(
        host_url=args.host_url,
        command_text=args.command,
        command_file=args.command_file,
        audio_file=args.audio_file,
        vlm_json_file=args.vlm_json_file,
        whisper_model=args.whisper_model,
        whisper_backend=args.whisper_backend,
        robot_id=args.robot_id,
        model_name=args.model_name,
        conf_threshold=args.conf_threshold,
    )

    try:
        client.run()
    finally:
        client.shutdown()


if __name__ == "__main__":
    main()
