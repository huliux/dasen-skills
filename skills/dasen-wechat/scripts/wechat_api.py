#!/usr/bin/env python3
"""Small WeChat draft API client owned by dasen-wechat."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from native_renderer import image_sources, replace_image_sources

CONTENT_SCRIPTS = Path(__file__).resolve().parents[2] / "dasen-content" / "scripts"
if str(CONTENT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CONTENT_SCRIPTS))

import network_safety  # noqa: E402

DOH_RESOLVER_ENV = network_safety.DOH_RESOLVER_ENV


API_ROOT = "https://api.weixin.qq.com/cgi-bin"
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_INLINE_IMAGE_BYTES = 1024 * 1024
Transport = Callable[[str, str, dict[str, str], bytes | None], dict[str, Any]]


class WechatApiError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


@dataclass(frozen=True)
class ImagePayload:
    source: str
    filename: str
    mime_type: str
    content: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


def _assert_wechat_success(data: dict[str, Any], operation: str) -> dict[str, Any]:
    code = data.get("errcode")
    if code not in (None, 0):
        message = str(data.get("errmsg") or "unknown error")
        raise WechatApiError(f"{operation} failed: WeChat {code}: {message}")
    return data


def _default_transport(method: str, url: str, headers: dict[str, str], body: bytes | None) -> dict[str, Any]:
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        raise WechatApiError(f"WeChat HTTP {exc.code}: {raw[:500].decode('utf-8', 'replace')}") from exc
    except urllib.error.URLError as exc:
        raise WechatApiError(f"WeChat network error: {exc.reason}") from exc
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WechatApiError("WeChat returned a non-JSON response") from exc
    if not isinstance(data, dict):
        raise WechatApiError("WeChat returned an unexpected JSON payload")
    return data


def _cache_dir() -> Path:
    root = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "dasen-wechat"
    root.mkdir(parents=True, exist_ok=True)
    try:
        root.chmod(0o700)
    except OSError:
        pass
    return root


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _safe_remote_url(source: str) -> urllib.parse.SplitResult:
    parsed = urllib.parse.urlsplit(source)
    try:
        port = parsed.port
    except ValueError as exc:
        raise WechatApiError(f"remote image URL has an invalid port: {_source_label(source)}") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or port not in {None, 443}
    ):
        raise WechatApiError(f"remote image must use an unauthenticated HTTPS URL: {_source_label(source)}")
    hostname = parsed.hostname
    public, reason = network_safety.resolve_public_addresses(hostname, port or 443)
    if not public:
        raise WechatApiError(f"remote image resolves to a non-public address: {hostname} ({reason})")
    return parsed


def _source_label(source: str) -> str:
    """Keep useful location context without persisting signed query parameters."""
    if source.startswith(("https://", "http://")):
        parsed = urllib.parse.urlsplit(source)
        host = parsed.hostname or "invalid-host"
        if ":" in host:
            host = f"[{host}]"
        return urllib.parse.urlunsplit((parsed.scheme, host, parsed.path, "", ""))
    return source


def _detect_image_type(content: bytes, filename: str) -> tuple[str, str]:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif", ".gif"
    if content.startswith(b"BM"):
        return "image/bmp", ".bmp"
    raise WechatApiError(f"unsupported or unrecognized image bytes: {filename}")


def load_image(source: str, base_dir: Path, allowed_local_root: Path | None = None) -> ImagePayload:
    if source.startswith(("https://", "http://")):
        parsed = _safe_remote_url(source)
        request = urllib.request.Request(source, headers={"User-Agent": "dasen-wechat/3"})
        opener = urllib.request.build_opener(_NoRedirect)
        try:
            with opener.open(request, timeout=30) as response:
                length = response.headers.get("Content-Length")
                try:
                    declared_size = int(length) if length else 0
                except ValueError as exc:
                    raise WechatApiError(f"remote image returned an invalid Content-Length: {_source_label(source)}") from exc
                if declared_size > MAX_IMAGE_BYTES:
                    raise WechatApiError(f"remote image exceeds 10 MiB: {_source_label(source)}")
                content = response.read(MAX_IMAGE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            if 300 <= exc.code < 400:
                raise WechatApiError(f"remote image redirects are not allowed: {_source_label(source)}") from exc
            raise WechatApiError(f"failed to download remote image: {_source_label(source)}: HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise WechatApiError(f"failed to download remote image: {_source_label(source)}: {exc.reason}") from exc
        filename = Path(urllib.parse.unquote(parsed.path)).name or "image"
    else:
        decoded = urllib.parse.unquote(source)
        raw = Path(decoded)
        if raw.is_absolute():
            raise WechatApiError(f"local image path must be relative: {_source_label(source)}")
        root = (allowed_local_root or base_dir).resolve()
        path = (base_dir / raw).resolve()
        if not path.is_relative_to(root):
            raise WechatApiError(f"local image escapes the configured asset root: {_source_label(source)}")
        if not path.is_file():
            raise WechatApiError(f"local image not found: {_source_label(source)}")
        if path.stat().st_size > MAX_IMAGE_BYTES:
            raise WechatApiError(f"local image exceeds 10 MiB: {_source_label(source)}")
        content = path.read_bytes()
        filename = path.name
    if not content:
        raise WechatApiError(f"empty image: {_source_label(source)}")
    if len(content) > MAX_IMAGE_BYTES:
        raise WechatApiError(f"image exceeds 10 MiB: {_source_label(source)}")
    mime_type, extension = _detect_image_type(content, filename)
    filename = (Path(filename).stem or "image") + extension
    return ImagePayload(source, filename, mime_type, content)


def multipart_image(payload: ImagePayload) -> tuple[bytes, str]:
    boundary = f"dasen-{uuid.uuid4().hex}"
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", payload.filename) or "image"
    chunks = [
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="media"; filename="{safe_name}"\r\n'.encode(),
        f"Content-Type: {payload.mime_type}\r\n\r\n".encode(),
        payload.content,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    return b"".join(chunks), boundary


class WechatClient:
    def __init__(self, app_id: str, app_secret: str, transport: Transport | None = None):
        if not app_id or not app_secret:
            raise WechatApiError("WeChat AppID and AppSecret are required")
        self.app_id = app_id
        self.app_secret = app_secret
        self.transport = transport or _default_transport
        self._upload_memory: dict[str, dict[str, str]] = {}

    def access_token(self) -> str:
        cache_path = _cache_dir() / "access-token-v1.json"
        cache = _load_json(cache_path)
        key = hashlib.sha256(self.app_id.encode()).hexdigest()
        item = cache.get(key) or {}
        if isinstance(item, dict) and item.get("token") and float(item.get("expires_at") or 0) > time.time() + 60:
            return str(item["token"])
        query = urllib.parse.urlencode({
            "appid": self.app_id,
            "secret": self.app_secret,
            "grant_type": "client_credential",
        })
        data = _assert_wechat_success(
            self.transport("GET", f"{API_ROOT}/token?{query}", {}, None),
            "access token",
        )
        token = str(data.get("access_token") or "")
        if not token:
            raise WechatApiError("access token response did not include access_token")
        cache[key] = {"token": token, "expires_at": time.time() + int(data.get("expires_in") or 7200) - 300}
        _save_json(cache_path, cache)
        return token

    def _upload(self, payload: ImagePayload, token: str, purpose: str) -> dict[str, str]:
        cache_key = f"{hashlib.sha256(self.app_id.encode()).hexdigest()}:{purpose}:{payload.sha256}"
        if cache_key in self._upload_memory:
            return self._upload_memory[cache_key]
        cache_path = _cache_dir() / "uploads-v1.json"
        cache = _load_json(cache_path)
        cached = cache.get(cache_key)
        if isinstance(cached, dict) and cached.get("url") and (purpose == "body" or cached.get("media_id")):
            result = {str(k): str(v) for k, v in cached.items() if k in {"url", "media_id"}}
            self._upload_memory[cache_key] = result
            return result

        body, boundary = multipart_image(payload)
        if purpose == "body" and payload.mime_type in {"image/png", "image/jpeg"} and len(payload.content) <= MAX_INLINE_IMAGE_BYTES:
            endpoint = f"{API_ROOT}/media/uploadimg?access_token={urllib.parse.quote(token)}"
            operation = "body image upload"
        else:
            endpoint = f"{API_ROOT}/material/add_material?access_token={urllib.parse.quote(token)}&type=image"
            operation = "permanent image upload"
        data = _assert_wechat_success(
            self.transport("POST", endpoint, {"Content-Type": f"multipart/form-data; boundary={boundary}"}, body),
            operation,
        )
        result = {key: str(data[key]) for key in ("url", "media_id") if data.get(key)}
        if not result.get("url"):
            raise WechatApiError(f"{operation} response did not include url")
        if purpose != "body" and not result.get("media_id"):
            raise WechatApiError(f"{operation} response did not include media_id")
        result["url"] = re.sub(r"^http://", "https://", result["url"], flags=re.I)
        cache[cache_key] = result
        _save_json(cache_path, cache)
        self._upload_memory[cache_key] = result
        return result

    def prepare_body_images(
        self,
        rendered_html: str,
        base_dir: Path,
        token: str,
        allowed_local_root: Path | None = None,
    ) -> str:
        replacements: dict[str, str] = {}
        for source in image_sources(rendered_html):
            parsed = urllib.parse.urlsplit(source)
            try:
                port = parsed.port
            except ValueError:
                port = -1
            if (
                parsed.scheme == "https"
                and (parsed.hostname or "").lower() == "mmbiz.qpic.cn"
                and port in {None, 443}
                and not parsed.username
                and not parsed.password
            ):
                continue
            payload = load_image(source, base_dir, allowed_local_root)
            replacements[source] = self._upload(payload, token, "body")["url"]
        return replace_image_sources(rendered_html, replacements)

    def upload_cover(
        self,
        source: str,
        base_dir: Path,
        token: str,
        allowed_local_root: Path | None = None,
    ) -> str:
        payload = load_image(source, base_dir, allowed_local_root)
        return self._upload(payload, token, "cover")["media_id"]

    def add_draft(self, article: dict[str, Any], token: str) -> str:
        body = json.dumps({"articles": [article]}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        endpoint = f"{API_ROOT}/draft/add?access_token={urllib.parse.quote(token)}"
        data = _assert_wechat_success(
            self.transport("POST", endpoint, {"Content-Type": "application/json; charset=utf-8"}, body),
            "draft add",
        )
        media_id = str(data.get("media_id") or "")
        if not media_id:
            raise WechatApiError("draft add response did not include media_id")
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,256}", media_id):
            raise WechatApiError("draft add response included an invalid media_id")
        return media_id

    def publish_article(
        self,
        metadata: dict[str, Any],
        rendered_html: str,
        base_dir: Path,
        allowed_local_root: Path | None = None,
        before_draft: Callable[[], None] | None = None,
    ) -> str:
        title = str(metadata.get("title") or "").strip()
        author = str(metadata.get("author") or "").strip()
        digest = str(metadata.get("digest") or metadata.get("description") or "").strip()
        cover = str(metadata.get("cover") or "").strip()
        source_url = str(metadata.get("source_url") or "").strip()
        if not title or len(title) > 32:
            raise WechatApiError("title is required and must not exceed 32 characters")
        if len(author) > 16:
            raise WechatApiError("author must not exceed 16 characters")
        if len(digest) > 120:
            raise WechatApiError("digest must not exceed 120 characters")
        visible_text = re.sub(r"\s+", "", html.unescape(re.sub(r"<[^>]+>", " ", rendered_html)))
        if len(visible_text) >= 20_000 or len(rendered_html.encode("utf-8")) >= 1024 * 1024:
            raise WechatApiError("rendered article exceeds WeChat content limits")
        if source_url and (len(source_url.encode("utf-8")) > 1024 or not source_url.startswith(("https://", "http://"))):
            raise WechatApiError("source_url must be HTTP(S) and no larger than 1 KiB")

        token = self.access_token()
        content = self.prepare_body_images(rendered_html, base_dir, token, allowed_local_root)
        if len(content.encode("utf-8")) >= 1024 * 1024:
            raise WechatApiError("rendered article exceeds WeChat content limits after image upload")
        article: dict[str, Any] = {
            "article_type": "news",
            "title": title,
            "author": author,
            "digest": digest,
            "content": content,
            "need_open_comment": 1 if metadata.get("need_open_comment") else 0,
            "only_fans_can_comment": 1 if metadata.get("only_fans_can_comment") else 0,
        }
        if cover:
            article["thumb_media_id"] = self.upload_cover(
                cover, base_dir, token, allowed_local_root
            )
        if source_url:
            article["content_source_url"] = source_url
        if before_draft:
            before_draft()
        return self.add_draft(article, token)
