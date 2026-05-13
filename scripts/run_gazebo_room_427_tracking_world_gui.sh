#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORLD_PATH="${REPO_ROOT}/Simulation/worlds/room_427_tracking_test.world"
MODELS_PATH="${REPO_ROOT}/Simulation/Models"
GUI_CONFIG_PATH="${REPO_ROOT}/Simulation/gui/room_427_tracking_gui.config"
DEFAULT_RENDER_BACKEND="opengl"
if [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
  DEFAULT_RENDER_BACKEND="metal"
fi
SERVER_BACKEND="${GZ_SERVER_RENDER_BACKEND:-${DEFAULT_RENDER_BACKEND}}"
GUI_BACKEND="${GZ_RENDER_BACKEND:-${DEFAULT_RENDER_BACKEND}}"
SERVER_PID=""

export GZ_SIM_RESOURCE_PATH="${MODELS_PATH}${GZ_SIM_RESOURCE_PATH:+:${GZ_SIM_RESOURCE_PATH}}"
export GZ_IP="${GZ_IP:-127.0.0.1}"
export GZ_RELAY="${GZ_RELAY:-127.0.0.1}"

cleanup() {
  if [[ -n "${SERVER_PID}" ]] && kill -0 "${SERVER_PID}" 2>/dev/null; then
    echo
    echo "Stopping background Gazebo server (pid ${SERVER_PID})..."
    kill "${SERVER_PID}" 2>/dev/null || true
    wait "${SERVER_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

echo "Launching Room 427 tracking-test demo with visible Gazebo GUI:"
echo "  ${WORLD_PATH}"
echo "Using Gazebo model path:"
echo "  ${MODELS_PATH}"
echo "Using Gazebo GUI config:"
echo "  ${GUI_CONFIG_PATH}"
echo "Using Gazebo transport IP:"
echo "  ${GZ_IP}"
echo "Using Gazebo transport relay:"
echo "  ${GZ_RELAY}"
echo "Using server render backend: ${SERVER_BACKEND}"
echo "Using GUI render backend: ${GUI_BACKEND}"
echo
echo "Starting background simulation server..."

gz sim \
  -s \
  -r \
  --headless-rendering \
  --render-engine-server-api-backend "${SERVER_BACKEND}" \
  --wait-for-assets \
  "${WORLD_PATH}" \
  &
SERVER_PID=$!

sleep 2

echo "Opening Gazebo GUI client with camera feed panel..."
echo "If the main 3D view is still blank, try forcing both renderers:"
echo "  GZ_SERVER_RENDER_BACKEND=metal GZ_RENDER_BACKEND=metal ./scripts/run_gazebo_room_427_tracking_world_gui.sh"
echo

gz sim \
  -g \
  --gui-config "${GUI_CONFIG_PATH}" \
  --render-engine-gui-api-backend "${GUI_BACKEND}" \
  "$@"
GUI_STATUS=$?

exit "${GUI_STATUS}"
