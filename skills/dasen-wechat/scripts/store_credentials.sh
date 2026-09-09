#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/python_runtime.sh"
if ! PYTHON_BIN="$(find_dasen_python)"; then
  echo "ERROR: no configured Python can load the WeChat runtime; run setup.sh first" >&2
  exit 2
fi

exec "$PYTHON_BIN" "$SCRIPT_DIR/wechat_credentials.py" store "$@"
