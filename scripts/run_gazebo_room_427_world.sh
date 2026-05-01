#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORLD_PATH="${REPO_ROOT}/Simulation/worlds/room_427.world"
MODELS_PATH="${REPO_ROOT}/Simulation/Models"

export GZ_SIM_RESOURCE_PATH="${MODELS_PATH}${GZ_SIM_RESOURCE_PATH:+:${GZ_SIM_RESOURCE_PATH}}"
export GZ_IP="${GZ_IP:-127.0.0.1}"


echo "Launching Room 427 world:"
echo "  ${WORLD_PATH}"
echo "Using Gazebo model path:"
echo "  ${MODELS_PATH}"
echo "Using Gazebo transport IP:"
echo "  ${GZ_IP}"
echo
echo "If Apple Silicon rendering is unstable, try:"
echo "  GZ_RENDER_BACKEND=metal ./scripts/run_gazebo_room_427_world.sh"

exec gz sim -r "${WORLD_PATH}" "$@"
