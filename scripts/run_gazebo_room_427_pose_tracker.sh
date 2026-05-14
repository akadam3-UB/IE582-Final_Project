#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"
export GZ_IP="${GZ_IP:-127.0.0.1}"
export GZ_RELAY="${GZ_RELAY:-127.0.0.1}"

exec .venv/bin/python scripts/pan_tilt_gazebo_pose_tracker.py \
  --pose-topic "/world/room_427_tracking_test/pose/info" \
  --gazebo-model-name pantilt \
  --command-file runtime_command.txt \
  --base-x 12.1 \
  --base-y 3.27 \
  --base-z 2.35 \
  --base-yaw-deg 180 \
  --initial-pan-deg 0 \
  --initial-tilt-deg 25 \
  --tilt-joint-offset-m 0.1425 \
  --sensor-forward-offset-m 0.072 \
  "$@"
