#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORLD_PATH="${REPO_ROOT}/Simulation/worlds/room_427.world"
MODELS_PATH="${REPO_ROOT}/Simulation/models"
DEFAULT_RENDER_BACKEND="opengl"
if [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
  DEFAULT_RENDER_BACKEND="metal"
fi
RENDER_BACKEND="${GZ_RENDER_BACKEND:-${DEFAULT_RENDER_BACKEND}}"

export GZ_SIM_RESOURCE_PATH="${MODELS_PATH}${GZ_SIM_RESOURCE_PATH:+:${GZ_SIM_RESOURCE_PATH}}"
export GZ_IP="${GZ_IP:-127.0.0.1}"
export GZ_RELAY="${GZ_RELAY:-127.0.0.1}"


echo "Launching Room 427 world:"
echo "  ${WORLD_PATH}"
echo "Using Gazebo model path:"
echo "  ${MODELS_PATH}"
echo "Using Gazebo transport IP:"
echo "  ${GZ_IP}"
echo "Using Gazebo transport relay:"
echo "  ${GZ_RELAY}"
echo "Using render backend:"
echo "  ${RENDER_BACKEND}"
echo
echo "If Apple Silicon rendering is unstable, retry with:"
echo "  GZ_RENDER_BACKEND=metal ./scripts/run_gazebo_room_427_world.sh"

exec gz sim \
  -r \
  --render-engine-api-backend "${RENDER_BACKEND}" \
  "${WORLD_PATH}" \
  "$@"
