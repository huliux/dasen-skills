#!/usr/bin/env python3
"""Optional, configuration-driven Volcano TOS asset adapter.

Dry-run is the default. ``--execute`` is required before credentials are read or
network requests are made. Secret values are never stored in project files.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import hmac
import mimetypes
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONTENT_SCRIPTS = Path(__file__).resolve().parents[2] / "dasen-content" / "scripts"
sys.path.insert(0, str(CONTENT_SCRIPTS))

from content_paths import control_reference, select_content_root
from project_config import assets_config, default_project_reference, load_project_reference  # noqa: E402


SERVICE = "s3"
SUPPORTED = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
MAX_ASSET_BYTES = 20 * 1024 * 1024
ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


@dataclass(frozen=True)
class TosConfig:
    endpoint: str
    endpoint_host: str
    region: str
    bucket: str
    public_base_url: str
    access_key_env: str | None
    secret_key_env: str | None
    keychain_service: str | None
    access_key_account: str | None
    secret_key_account: str | None


def _required(raw: dict[str, Any], key: str) -> str:
    value = str(raw.get(key) or "").strip()
    if not value:
        raise ValueError(f"assets.remote.{key} is required for provider tos")
    return value


def _https_base(value: str, field: str, *, allow_path: bool) -> tuple[str, urllib.parse.SplitResult]:
    parsed = urllib.parse.urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port not in {None, 443}
    ):
        raise ValueError(f"assets.remote.{field} must be a credential-free HTTPS base URL on port 443")
    if not allow_path and parsed.path not in {"", "/"}:
        raise ValueError(f"assets.remote.{field} must not contain a path")
    normalized_path = parsed.path.rstrip("/") if allow_path else ""
    normalized = urllib.parse.urlunsplit(("https", parsed.netloc, normalized_path, "", ""))
    return normalized, parsed


def parse_tos_config(project: dict[str, Any]) -> TosConfig:
    remote = assets_config(project)["remote"]
    if str(remote.get("provider") or "none") != "tos":
        raise ValueError("assets.remote.provider must be tos")
    endpoint, endpoint_parts = _https_base(_required(remote, "endpoint"), "endpoint", allow_path=False)
    public_base, _ = _https_base(
        _required(remote, "public_base_url"), "public_base_url", allow_path=True
    )
    region = _required(remote, "region")
    bucket = _required(remote, "bucket")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,126}", bucket):
        raise ValueError("assets.remote.bucket has an invalid value")

    access_env = str(remote.get("access_key_env") or "").strip() or None
    secret_env = str(remote.get("secret_key_env") or "").strip() or None
    if bool(access_env) != bool(secret_env):
        raise ValueError("assets.remote access_key_env and secret_key_env must be configured together")
    if any(value and not ENV_NAME.fullmatch(value) for value in (access_env, secret_env)):
        raise ValueError("assets.remote credential environment names are invalid")

    service = str(remote.get("keychain_service") or "").strip() or None
    access_account = str(remote.get("access_key_account") or "").strip() or None
    secret_account = str(remote.get("secret_key_account") or "").strip() or None
    if len([value for value in (service, access_account, secret_account) if value]) not in {0, 3}:
        raise ValueError(
            "assets.remote keychain_service/access_key_account/secret_key_account must be configured together"
        )
    if not access_env and not service:
        raise ValueError("assets.remote must configure an environment-name pair or a Keychain source")

    return TosConfig(
        endpoint=endpoint,
        endpoint_host=str(endpoint_parts.hostname),
        region=region,
        bucket=bucket,
        public_base_url=public_base,
        access_key_env=access_env,
        secret_key_env=secret_env,
        keychain_service=service,
        access_key_account=access_account,
        secret_key_account=secret_account,
    )


def keychain_value(service: str, account: str) -> str:
    if sys.platform != "darwin":
        return ""
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def read_credentials(config: TosConfig) -> tuple[str, str]:
    if config.access_key_env and config.secret_key_env:
        access_key = os.environ.get(config.access_key_env, "").strip()
        secret_key = os.environ.get(config.secret_key_env, "").strip()
        if bool(access_key) != bool(secret_key):
            raise RuntimeError("the configured TOS environment source contains only half a credential pair")
        if access_key and secret_key:
            return access_key, secret_key

    if config.keychain_service and config.access_key_account and config.secret_key_account:
        access_key = keychain_value(config.keychain_service, config.access_key_account)
        secret_key = keychain_value(config.keychain_service, config.secret_key_account)
        if bool(access_key) != bool(secret_key):
            raise RuntimeError("the configured TOS Keychain source contains only half a credential pair")
        if access_key and secret_key:
            return access_key, secret_key

    raise RuntimeError("TOS credentials were not found in any complete configured source")


def hmac_digest(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def object_url(base: str, key: str) -> str:
    return f"{base.rstrip('/')}/{urllib.parse.quote(key, safe='/-_.~')}"


def upload_image(
    key: str,
    path: Path,
    access_key: str,
    secret_key: str,
    config: TosConfig,
) -> tuple[int, str]:
    body = path.read_bytes()
    payload_hash = hashlib.sha256(body).hexdigest()
    now = datetime.datetime.now(datetime.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    encoded_key = urllib.parse.quote(key, safe="/-_.~")
    canonical_uri = f"/{encoded_key}"

    headers = {
        "host": config.endpoint_host,
        "x-amz-acl": "public-read",
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
    }
    signed_headers = ";".join(sorted(headers))
    canonical_headers = "".join(f"{name}:{headers[name]}\n" for name in sorted(headers))
    canonical_request = "\n".join(
        ["PUT", canonical_uri, "", canonical_headers, signed_headers, payload_hash]
    )

    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{config.region}/{SERVICE}/aws4_request"
    string_to_sign = "\n".join(
        [
            algorithm,
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    date_key = hmac_digest(("AWS4" + secret_key).encode("utf-8"), date_stamp)
    region_key = hmac_digest(date_key, config.region)
    service_key = hmac_digest(region_key, SERVICE)
    signing_key = hmac_digest(service_key, "aws4_request")
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (
        f"{algorithm} Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    request = urllib.request.Request(object_url(config.endpoint, key), data=body, method="PUT")
    request.add_header("x-amz-acl", "public-read")
    request.add_header("x-amz-content-sha256", payload_hash)
    request.add_header("x-amz-date", amz_date)
    request.add_header("Authorization", authorization)
    request.add_header(
        "Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    )
    request.add_header("Content-Length", str(len(body)))
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.status, payload_hash


def verify_public(url: str, expected_sha256: str, attempts: int = 3) -> None:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
            with urllib.request.urlopen(request, timeout=60) as response:
                content = response.read(MAX_ASSET_BYTES + 1)
            if len(content) > MAX_ASSET_BYTES:
                raise RuntimeError("public asset exceeds the verification size limit")
            actual = hashlib.sha256(content).hexdigest()
            if actual != expected_sha256:
                raise RuntimeError("public asset SHA-256 does not match the uploaded bytes")
            return
        except Exception as exc:  # noqa: BLE001 - reported after bounded retry
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise RuntimeError(f"public asset verification failed after {attempts} attempts: {last_error}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan or execute uploads through the configured optional TOS adapter."
    )
    parser.add_argument("src_dir", help="Project-relative directory inside assets.root")
    parser.add_argument("object_prefix")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--project-file", help="Project-relative config; auto-detected when omitted")
    parser.add_argument("--content-root", help="Workspace-relative content directory")
    parser.add_argument("--execute", action="store_true", help="Read credentials and perform network writes")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = args.project_root.expanduser().resolve()
    project_root = select_content_root(workspace, args.content_root, args.project_file)
    project_ref = control_reference(workspace, project_root, args.project_file) or default_project_reference(project_root)
    if not project_ref:
        print("error: TOS upload requires a project configuration", file=sys.stderr)
        return 2
    try:
        _, project = load_project_reference(project_ref, project_root)
        asset_settings = assets_config(project)
        config = parse_tos_config(project)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    raw_src = Path(args.src_dir)
    asset_root_value = Path(str(asset_settings["root"]))
    if raw_src.is_absolute() or asset_root_value.is_absolute():
        print("error: src_dir and assets.root must be project-relative", file=sys.stderr)
        return 2
    allowed_root = (project_root / asset_root_value).resolve()
    src_candidate = project_root / raw_src
    if src_candidate.is_symlink():
        print("error: src_dir must not be a symlink", file=sys.stderr)
        return 2
    src_dir = src_candidate.resolve()
    if not src_dir.is_relative_to(allowed_root) or not src_dir.is_dir():
        print("error: src_dir must be an existing directory inside assets.root", file=sys.stderr)
        return 2
    prefix = args.object_prefix.strip("/")
    if not prefix or ".." in Path(prefix).parts:
        print("error: object_prefix must be non-empty and must not contain '..'", file=sys.stderr)
        return 2

    entries = sorted(path for path in src_dir.iterdir() if path.suffix.lower() in SUPPORTED)
    if any(path.is_symlink() for path in entries):
        print("error: image symlinks are not allowed", file=sys.stderr)
        return 2
    files = [path for path in entries if path.is_file()]
    if not files:
        print("error: no supported images found", file=sys.stderr)
        return 2
    oversized = [path.name for path in files if path.stat().st_size > MAX_ASSET_BYTES]
    if oversized:
        print("error: one or more images exceed the 20 MiB adapter limit", file=sys.stderr)
        return 2

    if not args.execute:
        print(
            f"DRY-RUN: {len(files)} file(s); provider=tos; bucket={config.bucket}; "
            f"endpoint={config.endpoint_host}; no credentials or network used"
        )
        for path in files:
            key = f"{prefix}/{path.name}"
            print(f"- {path.name} -> {key} -> {object_url(config.public_base_url, key)}")
        return 0

    try:
        access_key, secret_key = read_credentials(config)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    failures: list[str] = []
    for path in files:
        key = f"{prefix}/{path.name}"
        public_url = object_url(config.public_base_url, key)
        try:
            status, sha256 = upload_image(key, path, access_key, secret_key, config)
            verify_public(public_url, sha256)
            print(f"OK {status} {path.name} sha256={sha256} -> {public_url}")
        except Exception as exc:  # noqa: BLE001 - per-file failure summary
            failures.append(path.name)
            print(f"FAIL {path.name}: {exc}", file=sys.stderr)

    if failures:
        print(f"error: {len(failures)} upload(s) failed", file=sys.stderr)
        return 1
    print(f"Uploaded and verified {len(files)} image(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
