#!/usr/bin/env python3
"""Drive the fourth-floor Ackermann car using its front camera.

The controller is deliberately vision-only: it thresholds the dark reflective
floor in the car camera, follows the center of the visible floor band, and
turns when the forward floor region disappears near a wall or door.
"""

from __future__ import annotations

import argparse
import math
import signal
import time
from typing import Optional, Tuple

import numpy as np

try:
    from gz.msgs10 import image_pb2
    from gz.msgs10.twist_pb2 import Twist
    from gz.transport13 import Node
except ImportError as exc:
    raise SystemExit(
        "Missing Gazebo Python bindings. Run from the project virtual "
        "environment used for Gazebo."
    ) from exc


_PIXEL_FORMAT_CHANNELS = {
    image_pb2.L_INT8: 1,
    image_pb2.RGB_INT8: 3,
    image_pb2.RGBA_INT8: 4,
    image_pb2.BGRA_INT8: 4,
    image_pb2.BGR_INT8: 3,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class FourthFloorHallwayDriver:
    def __init__(
        self,
        image_topic: str,
        cmd_topic: str,
        dark_threshold: int,
        base_speed: float,
        turn_speed: float,
        reverse_speed: float,
        steer_gain: float,
        max_steer: float,
        control_rate_hz: float,
        front_floor_min: float,
        reopen_floor_min: float,
        reverse_duration_s: float,
        turn_duration_s: float,
        invert_steering: bool,
    ) -> None:
        self.node = Node()
        self.image_topic = image_topic
        self.cmd_topic = cmd_topic
        self.dark_threshold = int(dark_threshold)
        self.base_speed = float(base_speed)
        self.turn_speed = float(turn_speed)
        self.reverse_speed = float(reverse_speed)
        self.steer_gain = float(steer_gain)
        self.max_steer = float(max_steer)
        self.control_interval_s = 1.0 / max(float(control_rate_hz), 0.1)
        self.front_floor_min = float(front_floor_min)
        self.reopen_floor_min = float(reopen_floor_min)
        self.reverse_duration_s = float(reverse_duration_s)
        self.turn_duration_s = float(turn_duration_s)
        self.steering_sign = -1.0 if invert_steering else 1.0

        self._latest_frame: Optional[np.ndarray] = None
        self._received_frame = False
        self._shutdown = False
        self._last_log_time = 0.0
        self._last_turn_dir = 1.0
        self._mode = "follow"
        self._mode_until = 0.0
        self._turn_dir = 1.0
        self._center_smooth: Optional[float] = None

        self.cmd_pub = self.node.advertise(self.cmd_topic, Twist)
        self.node.subscribe(image_pb2.Image, self.image_topic, self._on_image)
        self._install_signal_handlers()

    def _install_signal_handlers(self) -> None:
        def handle_signal(signum, frame):
            self._shutdown = True

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

    def _decode_image(self, msg: image_pb2.Image) -> Optional[np.ndarray]:
        width = int(msg.width)
        height = int(msg.height)
        channels = _PIXEL_FORMAT_CHANNELS.get(int(msg.pixel_format_type))
        if width <= 0 or height <= 0 or channels is None:
            return None

        row_bytes = int(msg.step) if int(msg.step) > 0 else width * channels
        raw = np.frombuffer(msg.data, dtype=np.uint8)
        if raw.size < height * row_bytes:
            return None

        rows = raw[: height * row_bytes].reshape(height, row_bytes)
        packed = rows[:, : width * channels]

        if int(msg.pixel_format_type) == image_pb2.L_INT8:
            gray = packed.reshape(height, width)
            return np.repeat(gray[:, :, None], 3, axis=2).copy()
        if int(msg.pixel_format_type) == image_pb2.RGB_INT8:
            return packed.reshape(height, width, channels)[:, :, ::-1].copy()
        if int(msg.pixel_format_type) == image_pb2.BGR_INT8:
            return packed.reshape(height, width, channels).copy()
        if int(msg.pixel_format_type) == image_pb2.RGBA_INT8:
            return packed.reshape(height, width, channels)[:, :, [2, 1, 0]].copy()
        if int(msg.pixel_format_type) == image_pb2.BGRA_INT8:
            return packed.reshape(height, width, channels)[:, :, :3].copy()
        return None

    def _on_image(self, msg: image_pb2.Image) -> None:
        frame = self._decode_image(msg)
        if frame is None:
            return
        self._latest_frame = frame
        self._received_frame = True

    def _publish_cmd(self, linear_x: float, angular_z: float) -> None:
        msg = Twist()
        msg.linear.x = float(linear_x)
        msg.angular.z = float(self.steering_sign * angular_z)
        self.cmd_pub.publish(msg)

    def _stop(self) -> None:
        for _ in range(4):
            self._publish_cmd(0.0, 0.0)
            time.sleep(0.03)

    def _floor_mask(self, frame: np.ndarray) -> np.ndarray:
        gray = (
            0.114 * frame[:, :, 0]
            + 0.587 * frame[:, :, 1]
            + 0.299 * frame[:, :, 2]
        )
        # The hallway floor is the dark reflective plane. Specular highlights
        # remain near it, so a simple luminance cutoff is more stable than
        # color-specific segmentation.
        return gray < self.dark_threshold

    def _floor_center_from_slices(self, mask: np.ndarray) -> Optional[float]:
        h, w = mask.shape
        centers = []
        weights = []
        fallback_centers = []
        fallback_weights = []
        for frac in (0.46, 0.54, 0.62, 0.70, 0.78, 0.86):
            y0 = int(max(0, min(h - 1, frac * h)))
            band = mask[y0 : min(h, y0 + max(4, h // 40)), :]
            xs = np.flatnonzero(band.mean(axis=0) > 0.12)
            if xs.size < 12:
                continue
            left = float(xs[0])
            right = float(xs[-1])
            width_frac = (right - left) / max(1.0, float(w))
            center = (left + right) * 0.5
            # Bands where the whole lower image is dark floor are useful for
            # "floor exists" but weak for centering, so keep them as fallback
            # instead of letting them dominate the perspective corridor center.
            if width_frac > 0.94:
                fallback_centers.append(center)
                fallback_weights.append(0.4)
                continue
            centers.append(center)
            weights.append(max(0.5, (0.92 - frac) * 3.0))
        if not centers:
            if not fallback_centers:
                return None
            return float(
                np.average(
                    np.asarray(fallback_centers),
                    weights=np.asarray(fallback_weights),
                )
            )
        return float(np.average(np.asarray(centers), weights=np.asarray(weights)))

    def _choose_turn_dir(self, mask: np.ndarray) -> float:
        h, w = mask.shape
        side_band = mask[int(0.52 * h) : int(0.86 * h), :]
        left_score = float(side_band[:, : w // 2].mean())
        right_score = float(side_band[:, w // 2 :].mean())
        if abs(left_score - right_score) < 0.025:
            return self._last_turn_dir
        return 1.0 if left_score > right_score else -1.0

    def _metrics(self, frame: np.ndarray) -> Tuple[Optional[float], float, float, float]:
        mask = self._floor_mask(frame)
        h, w = mask.shape
        center_x = self._floor_center_from_slices(mask)
        far = float(mask[int(0.40 * h) : int(0.58 * h), int(0.25 * w) : int(0.75 * w)].mean())
        middle = float(mask[int(0.56 * h) : int(0.74 * h), int(0.20 * w) : int(0.80 * w)].mean())
        lower = float(mask[int(0.72 * h) :, int(0.12 * w) : int(0.88 * w)].mean())
        forward_floor = 0.55 * middle + 0.45 * far
        return center_x, forward_floor, lower, self._choose_turn_dir(mask)

    def _control_once(self) -> None:
        frame = self._latest_frame
        if frame is None:
            return

        h, w = frame.shape[:2]
        center_x, forward_floor, lower_floor, suggested_turn = self._metrics(frame)
        now = time.monotonic()

        if self._mode == "reverse":
            if now >= self._mode_until:
                self._mode = "turn"
                self._mode_until = now + self.turn_duration_s
                linear = self.turn_speed
                angular = self._turn_dir * self.max_steer
            else:
                linear = self.reverse_speed
                angular = -self._turn_dir * self.max_steer
        elif self._mode == "turn":
            corridor_reopened = (
                center_x is not None
                and lower_floor >= 0.20
                and forward_floor >= self.reopen_floor_min
            )
            if now >= self._mode_until and corridor_reopened:
                self._mode = "follow"
                self._center_smooth = None
                linear = self.base_speed * 0.6
                angular = 0.0
            else:
                linear = self.turn_speed
                angular = self._turn_dir * self.max_steer
        else:
            if center_x is None or lower_floor < 0.08:
                self._mode = "reverse"
                self._turn_dir = suggested_turn
                self._last_turn_dir = self._turn_dir
                self._mode_until = now + self.reverse_duration_s
                linear = self.reverse_speed
                angular = -self._turn_dir * self.max_steer
            elif forward_floor < self.front_floor_min:
                self._mode = "reverse"
                self._turn_dir = suggested_turn
                self._last_turn_dir = self._turn_dir
                self._mode_until = now + self.reverse_duration_s
                linear = self.reverse_speed
                angular = -self._turn_dir * self.max_steer
            else:
                center_norm = center_x / max(1.0, float(w))
                if self._center_smooth is None:
                    self._center_smooth = center_norm
                else:
                    self._center_smooth = 0.65 * self._center_smooth + 0.35 * center_norm
                error = 2.0 * (0.5 - self._center_smooth)
                angular = _clamp(self.steer_gain * error, -self.max_steer, self.max_steer)
                front_clearance = _clamp(
                    (forward_floor - self.front_floor_min)
                    / max(0.01, 1.0 - self.front_floor_min),
                    0.0,
                    1.0,
                )
                speed_scale = max(0.45, 1.0 - abs(error) * 0.85)
                speed_scale *= 0.62 + 0.38 * front_clearance
                linear = self.base_speed * speed_scale

        self._publish_cmd(linear, angular)

        if now - self._last_log_time >= 0.5:
            center_txt = "none" if center_x is None else f"{center_x / w:.2f}"
            print(
                f"mode={self._mode:7s} center={center_txt} "
                f"front={forward_floor:.2f} lower={lower_floor:.2f} "
                f"cmd=(x={linear:.2f}, z={angular:.2f})"
            )
            self._last_log_time = now

    def run(self) -> None:
        print(f"Subscribed to camera: {self.image_topic}")
        print(f"Publishing drive commands: {self.cmd_topic}")
        print("Driving from dark reflective floor edges; Ctrl-C stops the car.")
        waiting_logged = False
        next_tick = time.monotonic()
        try:
            while not self._shutdown:
                if not self._received_frame:
                    if not waiting_logged:
                        print(f"Waiting for frames on {self.image_topic} ...")
                        waiting_logged = True
                    time.sleep(0.05)
                    continue

                now = time.monotonic()
                if now < next_tick:
                    time.sleep(min(0.02, next_tick - now))
                    continue
                next_tick = now + self.control_interval_s
                self._control_once()
        finally:
            self._stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Fourth-floor camera hallway driver")
    parser.add_argument("--image-topic", default="/ackermann/front_camera/image")
    parser.add_argument("--cmd-topic", default="/cmd_vel")
    parser.add_argument("--dark-threshold", type=int, default=105)
    parser.add_argument("--base-speed", type=float, default=0.24)
    parser.add_argument("--turn-speed", type=float, default=0.13)
    parser.add_argument("--reverse-speed", type=float, default=-0.18)
    parser.add_argument("--steer-gain", type=float, default=1.15)
    parser.add_argument("--max-steer", type=float, default=0.50)
    parser.add_argument("--control-rate-hz", type=float, default=10.0)
    parser.add_argument("--front-floor-min", type=float, default=0.72)
    parser.add_argument("--reopen-floor-min", type=float, default=0.88)
    parser.add_argument("--reverse-duration-s", type=float, default=1.35)
    parser.add_argument("--turn-duration-s", type=float, default=3.80)
    parser.add_argument("--invert-steering", action="store_true")
    args = parser.parse_args()

    driver = FourthFloorHallwayDriver(
        image_topic=args.image_topic,
        cmd_topic=args.cmd_topic,
        dark_threshold=args.dark_threshold,
        base_speed=args.base_speed,
        turn_speed=args.turn_speed,
        reverse_speed=args.reverse_speed,
        steer_gain=args.steer_gain,
        max_steer=args.max_steer,
        control_rate_hz=args.control_rate_hz,
        front_floor_min=args.front_floor_min,
        reopen_floor_min=args.reopen_floor_min,
        reverse_duration_s=args.reverse_duration_s,
        turn_duration_s=args.turn_duration_s,
        invert_steering=args.invert_steering,
    )
    driver.run()


if __name__ == "__main__":
    main()
