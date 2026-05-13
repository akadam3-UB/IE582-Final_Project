#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODELS_PATH="${REPO_ROOT}/Simulation/Models"
GUI_CONFIG_PATH="${REPO_ROOT}/Simulation/gui/room_427_camera_view.config"
DEFAULT_RENDER_BACKEND="opengl"
if [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
  DEFAULT_RENDER_BACKEND="metal"
fi
GUI_BACKEND="${GZ_RENDER_BACKEND:-${DEFAULT_RENDER_BACKEND}}"

export GZ_SIM_RESOURCE_PATH="${MODELS_PATH}${GZ_SIM_RESOURCE_PATH:+:${GZ_SIM_RESOURCE_PATH}}"
export GZ_IP="${GZ_IP:-127.0.0.1}"
export GZ_RELAY="${GZ_RELAY:-127.0.0.1}"

echo "Opening Room 427 pan/tilt camera POV:"
echo "  /world/room_427_tracking_test/model/pantilt/link/tilt_link/sensor/camera/image"
echo "Using Gazebo GUI config:"
echo "  ${GUI_CONFIG_PATH}"
echo "Using GUI render backend: ${GUI_BACKEND}"
echo
echo "This attaches to an already-running room_427_tracking_test server."

exec gz sim \
  -g \
  --gui-config "${GUI_CONFIG_PATH}" \
  --render-engine-gui-api-backend "${GUI_BACKEND}" \
  "$@"
