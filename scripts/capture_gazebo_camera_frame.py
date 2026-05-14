#!/usr/bin/env python3
"""Save one Gazebo camera image topic frame as a PNG/JPEG file."""

from __future__ import annotations

import argparse
import pathlib
import sys
import time
from typing import Optional

import cv2
import numpy as np

try:
    from gz.msgs10 import image_pb2
    from gz.transport13 import Node
except ImportError as exc:
    raise SystemExit(
        "Missing Gazebo Python bindings. Activate the project environment and "
        "run this while Gazebo is installed."
    ) from exc


PIXEL_FORMAT_CHANNELS = {
    image_pb2.L_INT8: 1,
    image_pb2.RGB_INT8: 3,
    image_pb2.RGBA_INT8: 4,
    image_pb2.BGRA_INT8: 4,
    image_pb2.BGR_INT8: 3,
}


def decode_image_message(msg: image_pb2.Image) -> Optional[np.ndarray]:
    width = int(msg.width)
    height = int(msg.height)
    pixel_format = int(msg.pixel_format_type)
    channels = PIXEL_FORMAT_CHANNELS.get(pixel_format)
    if width <= 0 or height <= 0 or channels is None:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture one Gazebo camera frame.")
    parser.add_argument(
        "--topic",
        default="/world/room_427/model/pantilt/link/tilt_link/sensor/camera/image",
        help="Gazebo image topic to subscribe to.",
    )
    parser.add_argument("--output", required=True, help="Output image path.")
    parser.add_argument("--timeout-sec", type=float, default=12.0)
    args = parser.parse_args()

    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    node = Node()
    frame_holder: dict[str, Optional[np.ndarray]] = {"frame": None}

    def on_image(msg: image_pb2.Image) -> None:
        if frame_holder["frame"] is None:
            frame_holder["frame"] = decode_image_message(msg)

    node.subscribe(image_pb2.Image, args.topic, on_image)

    deadline = time.monotonic() + args.timeout_sec
    while frame_holder["frame"] is None and time.monotonic() < deadline:
        time.sleep(0.05)

    node.unsubscribe(args.topic)

    frame = frame_holder["frame"]
    if frame is None:
        raise SystemExit(f"No decodable frame received from {args.topic}")

    if not cv2.imwrite(str(output), frame):
        raise SystemExit(f"Could not write image to {output}")
    print(output)


if __name__ == "__main__":
    main()
