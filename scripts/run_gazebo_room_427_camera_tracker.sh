#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/.venv/bin/python}"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

cd "${REPO_ROOT}"
export GZ_IP="${GZ_IP:-127.0.0.1}"
export GZ_RELAY="${GZ_RELAY:-127.0.0.1}"

exec "${PYTHON_BIN}" scripts/pan_tilt_gazebo_tracker.py \
  --detector color-proxy \
  --topic "/world/room_427/model/pantilt/link/tilt_link/sensor/camera/image" \
  --gazebo-model-name pantilt \
  --command-file runtime_command.txt \
  --control-mode pose \
  --world-name room_427 \
  --model-pose-x 11.25 \
  --model-pose-y 3.25 \
  --model-pose-z 2.35 \
  --model-base-yaw-deg 0 \
  --initial-pan-deg 0 \
  --initial-tilt-deg 18 \
  --pan-min-deg -45 \
  --pan-max-deg 45 \
  --tilt-min-deg 0 \
  --tilt-max-deg 90 \
  --pan-deadband-px 24 \
  --tilt-deadband-px 28 \
  --tilt-setpoint-y-fraction 0.50 \
  --vertical-fov-deg 46.8 \
  --gain-scale 0.16 \
  --max-step-deg 0.50 \
  --control-rate-hz 4 \
  "$@"
