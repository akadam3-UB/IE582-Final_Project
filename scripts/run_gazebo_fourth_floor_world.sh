#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORLD_PATH="${REPO_ROOT}/Simulation/worlds/fourth_floor.world"
MODELS_PATH="${REPO_ROOT}/Simulation/Models"

export GZ_SIM_RESOURCE_PATH="${MODELS_PATH}${GZ_SIM_RESOURCE_PATH:+:${GZ_SIM_RESOURCE_PATH}}"

echo "Launching Bell Hall 4th-floor world:"
echo "  ${WORLD_PATH}"
echo "Using Gazebo model path:"
echo "  ${MODELS_PATH}"
echo
echo "If Apple Silicon rendering is unstable, try:"
echo "  GZ_RENDER_BACKEND=metal ./scripts/run_gazebo_fourth_floor_world.sh"

exec gz sim "${WORLD_PATH}" "$@"
