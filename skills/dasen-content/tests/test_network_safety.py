from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import network_safety  # noqa: E402
import preflight  # noqa: E402


def fake_ip_answers(host: str, port: int, **_: object) -> list[tuple[int, int, int, str, tuple[str, int]]]:
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("198.18.1.9", port))]


def test_fake_ip_requires_explicit_public_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(network_safety.socket, "getaddrinfo", fake_ip_answers)
    monkeypatch.delenv(network_safety.DOH_RESOLVER_ENV, raising=False)
    called = False

    def unexpected(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True
        raise AssertionError("no resolver should be called without explicit configuration")

    monkeypatch.setattr(network_safety.urllib.request, "build_opener", unexpected)
    public, reason = network_safety.resolve_public_addresses("cdn.example.test")
    assert public is False and "显式 DoH" in reason
    assert called is False


def test_preflight_uses_shared_fake_ip_decision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(network_safety.socket, "getaddrinfo", fake_ip_answers)
    monkeypatch.setattr(
        network_safety,
        "doh_public_addresses_with_reason",
        lambda hostname: (["203.0.113.8"], "test non-public answer"),
    )
    assert preflight.public_url_error("https://cdn.example.test/image.png") is not None

    monkeypatch.setattr(
        network_safety,
        "doh_public_addresses_with_reason",
        lambda hostname: (["8.8.8.8"], ""),
    )
    assert preflight.public_url_error("https://cdn.example.test/image.png") is None


class FakeResponse:
    def __init__(self, payload: bytes, content_type: str) -> None:
        self.payload = payload
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self, _: int) -> bytes:
        return self.payload


def test_json_doh_contract_reports_binary_endpoint_instead_of_generic_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(network_safety.socket, "getaddrinfo", fake_ip_answers)
    monkeypatch.setenv(network_safety.DOH_RESOLVER_ENV, "https://resolver.example/dns-query")
    opener = type("Opener", (), {"open": lambda self, request, timeout: FakeResponse(b"\x00\x01", "application/dns-message")})()
    monkeypatch.setattr(network_safety.urllib.request, "build_opener", lambda *_: opener)

    public, reason = network_safety.resolve_public_addresses("cdn.example.test")

    assert public is False
    assert "JSON" in reason and "RFC8484" in reason


def test_json_doh_contract_accepts_public_a_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(network_safety.socket, "getaddrinfo", fake_ip_answers)
    monkeypatch.setenv(network_safety.DOH_RESOLVER_ENV, "https://resolver.example/resolve")
    payload = b'{"Answer": [{"type": 1, "data": "8.8.8.8"}]}'
    opener = type("Opener", (), {"open": lambda self, request, timeout: FakeResponse(payload, "application/json")})()
    monkeypatch.setattr(network_safety.urllib.request, "build_opener", lambda *_: opener)

    public, reason = network_safety.resolve_public_addresses("cdn.example.test")

    assert public is True and reason == ""
