#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORLD_PATH="${REPO_ROOT}/worlds/pantilt_people_test.sdf"
RENDER_BACKEND="${GZ_RENDER_BACKEND:-opengl}"

export GZ_SIM_RESOURCE_PATH="${REPO_ROOT}/worlds:${REPO_ROOT}/models:${GZ_SIM_RESOURCE_PATH:-}"

echo "Launching temporary pan/tilt test world:"
echo "  ${WORLD_PATH}"
echo
echo "First launch may download actor assets from Gazebo Fuel."
echo "Using headless server mode with render backend: ${RENDER_BACKEND}"
echo "Set GZ_RENDER_BACKEND=metal to try Metal on Apple Silicon if needed."

exec gz sim \
  -s \
  -r \
  --headless-rendering \
  --render-engine-server-api-backend "${RENDER_BACKEND}" \
  --wait-for-assets \
  "${WORLD_PATH}" \
  "$@"
