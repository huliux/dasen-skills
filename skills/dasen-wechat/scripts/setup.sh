#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/python_runtime.sh"
if ! PYTHON_BIN="$(find_dasen_python)"; then
  echo "ERROR: no Python 3.10+ environment has PyYAML, markdown-it-py and Pygments" >&2
  echo "Install with your environment manager from: $SKILL_DIR/requirements.txt" >&2
  echo "Then set DASEN_PYTHON if that interpreter is not on PATH" >&2
  exit 2
fi

"$PYTHON_BIN" - <<'PY'
import sys

if sys.version_info < (3, 10):
    raise SystemExit("ERROR: dasen-wechat requires Python 3.10+")

missing = []
for module, package in (("yaml", "PyYAML"), ("markdown_it", "markdown-it-py"), ("pygments", "Pygments")):
    try:
        __import__(module)
    except ImportError:
        missing.append(package)
if missing:
    raise SystemExit("ERROR: missing Python packages: " + ", ".join(missing))
print("PASS: native render dependencies are ready")
PY

echo "Python: $PYTHON_BIN"
echo "Requirements: $SKILL_DIR/requirements.txt"
echo "Credential tools: project/device locators only; run $SCRIPT_DIR/wechat_credentials.py --help"
