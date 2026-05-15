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

set +e
"${PYTHON_BIN}" scripts/fourth_floor_hallway_driver.py "$@"
status=$?
set -e

if [[ "${status}" -eq 139 ]]; then
  echo "Gazebo transport closed after stopping the driver."
  exit 0
fi

exit "${status}"
