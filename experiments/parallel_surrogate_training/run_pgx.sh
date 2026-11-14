#!/usr/bin/env bash
# Invoke inside each Fuzzball GPU job with this folder mounted and shared paths.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
if [[ $# -lt 3 ]]; then
  echo "Usage: bash run_pgx.sh CONFIG OUTPUT SNAPSHOT [PREVIOUS_LAST_PT]" >&2
  exit 2
fi
"$PYTHON" "$HERE/preflight.py"
ARGS=(--config "$1" --output "$2" --snapshot "$3" --device cuda)
if [[ $# -ge 4 ]]; then ARGS+=(--resume "$4"); fi
exec "$PYTHON" "$HERE/train.py" "${ARGS[@]}"
