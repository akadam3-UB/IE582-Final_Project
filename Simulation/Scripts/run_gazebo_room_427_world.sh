#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORLD_PATH="${REPO_ROOT}/worlds/room_427.world"
RENDER_BACKEND="${GZ_RENDER_BACKEND:-opengl}"

export GZ_SIM_RESOURCE_PATH="${REPO_ROOT}/worlds:${REPO_ROOT}/models:${GZ_SIM_RESOURCE_PATH:-}"

echo "Launching 4th-floor Room 427 Gazebo world:"
echo "  ${WORLD_PATH}"
echo
echo "Using render backend: ${RENDER_BACKEND}"
exec gz sim \
  --render-engine-server-api-backend "${RENDER_BACKEND}" \
  "${WORLD_PATH}" \
  "$@"
