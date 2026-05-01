#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

if [[ ! -f ".venv/bin/python" ]]; then
  echo "Missing .venv in ${REPO_ROOT}. Create or activate the project-local environment first." >&2
  exit 1
fi

if [[ ! -f "runtime_command.txt" ]]; then
  printf 'track the person on the left\n' > "runtime_command.txt"
fi

exec .venv/bin/python scripts/pan_tilt_gazebo_pose_tracker.py \
  --pose-topic "/world/default/pose/info" \
  --gazebo-model-name pantilt \
  --command-file runtime_command.txt \
  "$@"
