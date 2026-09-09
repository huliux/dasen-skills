from __future__ import annotations

import json
import socket
import sys
import urllib.error
from pathlib import Path

import pytest


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import wechat_api  # noqa: E402
from wechat_api import ImagePayload, WechatApiError, WechatClient, _safe_remote_url, load_image  # noqa: E402


PNG = b"\x89PNG\r\n\x1a\n" + b"test-png"
GIF = b"GIF89a" + b"test-gif"


def test_publish_uses_inline_image_cover_material_and_draft_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    (tmp_path / "body.png").write_bytes(PNG)
    (tmp_path / "cover.png").write_bytes(PNG + b"cover")
    calls: list[tuple[str, str, dict[str, str], bytes | None]] = []

    def transport(method: str, url: str, headers: dict[str, str], body: bytes | None):
        calls.append((method, url, headers, body))
        if "/token?" in url:
            return {"access_token": "test-token", "expires_in": 7200}
        if "/media/uploadimg?" in url:
            return {"errcode": 0, "errmsg": "ok", "url": "http://mmbiz.qpic.cn/body"}
        if "/material/add_material?" in url:
            return {"media_id": "cover-media", "url": "http://mmbiz.qpic.cn/cover"}
        if "/draft/add?" in url:
            payload = json.loads((body or b"").decode("utf-8"))
            article = payload["articles"][0]
            assert article["thumb_media_id"] == "cover-media"
            assert article["digest"] == "摘要"
            assert 'src="https://mmbiz.qpic.cn/body"' in article["content"]
            return {"media_id": "draft-media"}
        raise AssertionError(url)

    client = WechatClient("app-test-one", "secret-test", transport)
    media_id = client.publish_article(
        {"title": "标题", "author": "作者", "digest": "摘要", "cover": "cover.png"},
        '<section><img src="body.png" /></section>',
        tmp_path,
    )
    assert media_id == "draft-media"
    assert any("/media/uploadimg?" in url for _, url, _, _ in calls)
    assert any("/material/add_material?" in url for _, url, _, _ in calls)
    assert any("/draft/add?" in url for _, url, _, _ in calls)


def test_gif_body_uses_permanent_image_endpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    (tmp_path / "follow.gif").write_bytes(GIF)
    calls: list[str] = []

    def transport(method: str, url: str, headers: dict[str, str], body: bytes | None):
        calls.append(url)
        return {"media_id": "gif-media", "url": "https://mmbiz.qpic.cn/follow"}

    client = WechatClient("app-test-two", "secret-test", transport)
    rendered = client.prepare_body_images('<img src="follow.gif" />', tmp_path, "token")
    assert 'src="https://mmbiz.qpic.cn/follow"' in rendered
    assert len(calls) == 1 and "/material/add_material?" in calls[0]


def test_private_or_insecure_remote_images_are_rejected() -> None:
    with pytest.raises(WechatApiError, match="HTTPS"):
        _safe_remote_url("http://example.com/image.png")
    with pytest.raises(WechatApiError, match="non-public"):
        _safe_remote_url("https://127.0.0.1/image.png")


def _fake_getaddrinfo(host: str, port: int, **_: object) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("198.18.1.9", port))]


def test_fake_ip_dns_with_doh_public_answer_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
    monkeypatch.setattr(
        wechat_api.network_safety,
        "doh_public_addresses_with_reason",
        lambda host: (["220.181.116.103"], ""),
    )
    assert _safe_remote_url("https://cdn.example.com/image.png").hostname == "cdn.example.com"


def test_fake_ip_dns_fails_closed_when_doh_cannot_confirm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
    monkeypatch.setattr(wechat_api.network_safety, "doh_public_addresses", lambda host: [])
    with pytest.raises(WechatApiError, match="non-public"):
        _safe_remote_url("https://cdn.example.com/image.png")


def test_fake_ip_dns_fails_closed_when_doh_returns_private(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
    monkeypatch.setattr(wechat_api.network_safety, "doh_public_addresses", lambda host: ["10.0.0.5"])
    with pytest.raises(WechatApiError, match="non-public"):
        _safe_remote_url("https://cdn.example.com/image.png")


def test_fake_ip_dns_has_no_implicit_doh_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
    monkeypatch.delenv(wechat_api.DOH_RESOLVER_ENV, raising=False)
    called = False

    def unexpected(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True
        raise AssertionError("network should not be used without explicit resolver configuration")

    monkeypatch.setattr(wechat_api.network_safety.urllib.request, "build_opener", unexpected)
    with pytest.raises(WechatApiError, match="non-public"):
        _safe_remote_url("https://cdn.example.com/image.png")
    assert called is False


def test_wechat_error_payload_is_not_treated_as_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    def transport(method: str, url: str, headers: dict[str, str], body: bytes | None):
        return {"errcode": 40013, "errmsg": "invalid appid"}

    with pytest.raises(WechatApiError, match="40013"):
        WechatClient("app-test-three", "secret-test", transport).access_token()


def test_image_extension_cannot_spoof_file_content(tmp_path: Path) -> None:
    (tmp_path / "fake.png").write_bytes(b"plain text")
    with pytest.raises(WechatApiError, match="image bytes"):
        load_image("fake.png", tmp_path)


def test_local_image_must_resolve_inside_configured_asset_root(tmp_path: Path) -> None:
    article_dir = tmp_path / "writing" / "2026-09-07" / "sample"
    asset_root = tmp_path / "assets"
    article_dir.mkdir(parents=True)
    asset_root.mkdir()
    (asset_root / "safe.png").write_bytes(PNG)
    (tmp_path / "secret.png").write_bytes(PNG)

    payload = load_image("../../../assets/safe.png", article_dir, asset_root)
    assert payload.filename == "safe.png"
    with pytest.raises(WechatApiError, match="asset root") as caught:
        load_image("../../../secret.png", article_dir, asset_root)
    assert str(tmp_path) not in str(caught.value)


def test_local_image_symlink_cannot_escape_configured_asset_root(tmp_path: Path) -> None:
    article_dir = tmp_path / "writing" / "sample"
    asset_root = tmp_path / "assets"
    article_dir.mkdir(parents=True)
    asset_root.mkdir()
    outside = tmp_path / "outside.png"
    outside.write_bytes(PNG)
    (asset_root / "link.png").symlink_to(outside)
    with pytest.raises(WechatApiError, match="asset root"):
        load_image("../../assets/link.png", article_dir, asset_root)


@pytest.mark.parametrize(
    "source",
    [
        "https://mmbiz.qpic.cn.evil.example/image.png",
        "https://mmbiz.qpic.cn:444/image.png",
    ],
)
def test_spoofed_or_nonstandard_wechat_image_url_is_uploaded(
    source: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    calls: list[str] = []
    payload = ImagePayload("source", "image.png", "image/png", PNG)
    monkeypatch.setattr(wechat_api, "load_image", lambda *args: payload)

    def transport(method: str, url: str, headers: dict[str, str], body: bytes | None):
        calls.append(url)
        return {"url": "https://mmbiz.qpic.cn/uploaded"}

    client = WechatClient("app-host-test", "secret-test", transport)
    rendered = client.prepare_body_images(f'<img src="{source}" />', tmp_path, "token")
    assert len(calls) == 1
    assert 'src="https://mmbiz.qpic.cn/uploaded"' in rendered


def test_publish_without_cover_omits_thumb_and_defers_platform_requirement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    def transport(method: str, url: str, headers: dict[str, str], body: bytes | None):
        if "/token?" in url:
            return {"access_token": "test-token", "expires_in": 7200}
        if "/draft/add?" in url:
            article = json.loads((body or b"").decode("utf-8"))["articles"][0]
            assert "thumb_media_id" not in article
            return {"media_id": "draft-without-cover"}
        raise AssertionError(url)

    media_id = WechatClient("app-no-cover", "secret-test", transport).publish_article(
        {"title": "标题", "author": "作者", "digest": "摘要"},
        "<section>正文内容足够用于测试平台负载边界</section>",
        tmp_path,
    )
    assert media_id == "draft-without-cover"


def test_remote_redirect_is_blocked_and_query_is_redacted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        wechat_api.network_safety.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("93.184.216.34", 443))],
    )

    class RedirectingOpener:
        def open(self, request, timeout):  # type: ignore[no-untyped-def]
            raise urllib.error.HTTPError(request.full_url, 302, "redirect", {}, None)

    monkeypatch.setattr("wechat_api.urllib.request.build_opener", lambda *args: RedirectingOpener())
    with pytest.raises(WechatApiError) as caught:
        load_image("https://example.com/image.png?secret=signed", tmp_path)
    assert "redirects are not allowed" in str(caught.value)
    assert "secret=signed" not in str(caught.value)
