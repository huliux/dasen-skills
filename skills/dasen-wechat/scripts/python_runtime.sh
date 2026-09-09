#!/usr/bin/env bash

dasen_python_ready() {
  local candidate="$1"
  [[ -x "$candidate" ]] || command -v "$candidate" >/dev/null 2>&1 || return 1
  "$candidate" -c 'import sys, yaml, markdown_it, pygments; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
    >/dev/null 2>&1
}

find_dasen_python() {
  local candidate version prefix
  if [[ -n "${DASEN_PYTHON:-}" ]]; then
    dasen_python_ready "$DASEN_PYTHON" && printf '%s\n' "$DASEN_PYTHON" && return 0
    return 1
  fi

  for candidate in python3 python3.13 python3.12 python3.11 python3.10; do
    if dasen_python_ready "$candidate"; then
      command -v "$candidate"
      return 0
    fi
  done

  if command -v pyenv >/dev/null 2>&1; then
    while IFS= read -r version; do
      [[ -n "$version" ]] || continue
      prefix="$(pyenv prefix "$version" 2>/dev/null || true)"
      candidate="$prefix/bin/python3"
      if dasen_python_ready "$candidate"; then
        printf '%s\n' "$candidate"
        return 0
      fi
    done < <(pyenv versions --bare 2>/dev/null)
  fi
  return 1
}
