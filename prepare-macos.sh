#!/bin/sh
# Run only from a complete artifact obtained through a verified release channel.
set -eu
umask 077
if [ "${1:-}" = '--help' ]; then
    printf '%s\n' 'Usage: /bin/sh <artifact>/prepare-macos.sh [--repair]' \
        'Prepares a local runtime only; does not enable any project or host.' \
        'Default storage: ~/Library/Application Support/dasen-skills' \
        'DASEN_DATA_ROOT may select a separate absolute storage path for testing.'
    exit 0
fi
case "${1:-}" in ''|--repair) ;; *) printf '%s\n' 'ERROR: expected --repair or no arguments' >&2; exit 1 ;; esac
[ "$#" -le 1 ] || exit 1
[ "$(/usr/bin/uname -s)" = Darwin ] || { printf '%s\n' 'ERROR: macOS is required' >&2; exit 1; }
artifact=$(CDPATH= cd -- "$(/usr/bin/dirname -- "$0")" && pwd -P)
[ -f "$artifact/artifact-manifest.json" ] || { printf '%s\n' 'ERROR: use a complete built artifact with its manifest' >&2; exit 1; }
data=${DASEN_DATA_ROOT:-"$HOME/Library/Application Support/dasen-skills"}
data=${data%/}
case "$data" in */../*|*/./*|*/..|*/.) printf '%s\n' 'ERROR: use a normalized absolute data path' >&2; exit 1 ;; esac
case "$artifact/" in "$data/"*) printf '%s\n' 'ERROR: data storage and artifact must be separate trees' >&2; exit 1 ;; esac
case "$data" in /*) ;; *) printf '%s\n' 'ERROR: data storage must be an absolute path' >&2; exit 1 ;; esac
# Resolve the existing ancestor before creating storage; reject artifact nesting.
ancestor=$data
while [ ! -d "$ancestor" ]; do ancestor=$(/usr/bin/dirname -- "$ancestor"); done
ancestor=$(CDPATH= cd -- "$ancestor" && pwd -P)
case "$ancestor/" in "$artifact/"*) printf '%s\n' 'ERROR: data storage must be outside the artifact' >&2; exit 1 ;; esac
# uv owns managed Python and download caches in its usual user locations.
# A version-pinned uv executable is private to this route; shell profiles are untouched.
version=0.12.10
case "$(/usr/bin/uname -m)" in
    arm64)
        target=aarch64-apple-darwin
        archive_hash=51c6170e8e3a01cef9f33b94f582b7b81ac65046f55d40afb35f9cff5a68c179
        binary_hash=bee807eb1c018d8cc90b4ed83d61612cb22aa47be2073f63f209fa5610862cdb ;;
    x86_64)
        target=x86_64-apple-darwin
        archive_hash=5296d5aa2b9143360405eea866f8ef4d5dc8986b164eb0dc35e8f876a9304d30
        binary_hash=7bf5a995977aedd27373b841051af564886e956437d01cfff21bc325678c7b7e ;;
    *) printf '%s\n' 'ERROR: unsupported macOS architecture' >&2; exit 1 ;;
esac
hash_file() { /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'; }
uv="$data/tools/uv-$version-$target"
[ ! -L "$data/tools" ] || { printf '%s\n' 'ERROR: tools directory is a link; resolve ownership first' >&2; exit 1; }
/bin/mkdir -p "$data/tools"
if [ ! -e "$uv" ] && [ ! -L "$uv" ]; then
    temporary=$(/usr/bin/mktemp -d "$data/tools/.download-XXXXXX")
    trap '/bin/rm -rf "$temporary"' EXIT
    trap 'exit 1' HUP INT TERM
    url="https://github.com/astral-sh/uv/releases/download/$version/uv-$target.tar.gz"
    printf '%s\n' 'Preparing pinned uv from the official release...' >&2
    if ! /usr/bin/curl --disable --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
        --tlsv1.2 --connect-timeout 15 --max-time 180 --retry 2 --retry-max-time 210 \
        "$url" -o "$temporary/uv.tar.gz"; then
        printf '%s\n' 'ERROR: uv download failed. Check access to GitHub release downloads and retry; no host was enabled.' >&2
        exit 1
    fi
    [ "$(hash_file "$temporary/uv.tar.gz")" = "$archive_hash" ] || { printf '%s\n' 'ERROR: uv archive checksum mismatch; download rejected' >&2; exit 1; }
    /usr/bin/tar -xzf "$temporary/uv.tar.gz" -C "$temporary" "uv-$target/uv"
    [ "$(hash_file "$temporary/uv-$target/uv")" = "$binary_hash" ] || exit 1
    /bin/mv -n "$temporary/uv-$target/uv" "$uv"
fi
[ ! -L "$uv" ] && [ "$(hash_file "$uv")" = "$binary_hash" ] || { printf '%s\n' 'ERROR: existing uv executable changed; preserve it and resolve the conflicting file' >&2; exit 1; }
# Ignore project Python selection, active venvs and uv configuration during bootstrap.
unset VIRTUAL_ENV PYTHONHOME PYTHONPATH UV_PYTHON UV_PYTHON_PREFERENCE UV_NO_MANAGED_PYTHON UV_PYTHON_DOWNLOADS UV_PYTHON_INSTALL_MIRROR UV_PYPY_INSTALL_MIRROR UV_CONFIG_FILE
export UV_NO_CONFIG=1
export PYTHONDONTWRITEBYTECODE=1
if ! "$uv" --no-config python install 3.13.15 --no-bin >/dev/null 2>&1; then
    printf '%s\n' 'ERROR: managed Python preparation failed. Check official Python download connectivity, disk space and permissions, then retry.' >&2
    exit 1
fi
python=$("$uv" --no-config python find 3.13.15 --managed-python --no-project --system)
if [ -n "${temporary:-}" ]; then /bin/rm -rf "$temporary"; trap - EXIT HUP INT TERM; fi
exec "$python" -B "$artifact/skills/dasen-content/scripts/prepare_runtime.py" \
    --artifact-root "$artifact" --data-root "$data" --uv "$uv" "$@"
