#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/python_runtime.sh"
if ! PYTHON_BIN="$(find_dasen_python)"; then
  echo "ERROR: no Python 3.10+ environment has PyYAML, markdown-it-py and Pygments" >&2
  echo "Run setup.sh after installing requirements.txt, or set DASEN_PYTHON explicitly" >&2
  exit 2
fi
exec "$PYTHON_BIN" "$SCRIPT_DIR/native_publish.py" "$@"
