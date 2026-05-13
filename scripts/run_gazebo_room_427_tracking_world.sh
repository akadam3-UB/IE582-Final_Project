#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORLD_PATH="${REPO_ROOT}/Simulation/worlds/room_427_tracking_test.world"
MODELS_PATH="${REPO_ROOT}/Simulation/Models"
DEFAULT_RENDER_BACKEND="opengl"
if [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
  DEFAULT_RENDER_BACKEND="metal"
fi
RENDER_BACKEND="${GZ_RENDER_BACKEND:-${DEFAULT_RENDER_BACKEND}}"

export GZ_SIM_RESOURCE_PATH="${MODELS_PATH}${GZ_SIM_RESOURCE_PATH:+:${GZ_SIM_RESOURCE_PATH}}"
export GZ_IP="${GZ_IP:-127.0.0.1}"
export GZ_RELAY="${GZ_RELAY:-127.0.0.1}"


echo "Launching Room 427 tracking-test world:"
echo "  ${WORLD_PATH}"
echo "Using Gazebo model path:"
echo "  ${MODELS_PATH}"
echo "Using Gazebo transport IP:"
echo "  ${GZ_IP}"
echo "Using Gazebo transport relay:"
echo "  ${GZ_RELAY}"
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
