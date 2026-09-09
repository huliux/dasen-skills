#!/usr/bin/env python3
"""Shared, fail-closed hostname checks for remotely fetched content assets."""

from __future__ import annotations

import ipaddress
import json
import os
import socket
import urllib.parse
import urllib.request


FAKE_IP_NETWORK = ipaddress.ip_network("198.18.0.0/15")
DOH_RESOLVER_ENV = "DASEN_DOH_RESOLVER_URL"
MAX_DOH_RESPONSE_BYTES = 64 * 1024


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def addresses_public(ips: list[str]) -> bool:
    for value in ips:
        address = ipaddress.ip_address(value.split("%", 1)[0])
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            return False
    return bool(ips)


def all_fake_ip(ips: list[str]) -> bool:
    """Return true only for the benchmark range commonly used by fake-IP proxies."""
    return bool(ips) and all(
        ipaddress.ip_address(value.split("%", 1)[0]) in FAKE_IP_NETWORK for value in ips
    )


def doh_public_addresses_with_reason(hostname: str) -> tuple[list[str], str]:
    """Resolve through an explicitly configured HTTPS JSON resolver with diagnostics.

    The resolver is never selected implicitly. A configured resolver may itself be
    represented by a fake-IP address because the local proxy owns that route; any
    other non-public resolver address fails closed.
    """
    resolver = os.environ.get(DOH_RESOLVER_ENV, "").strip()
    if not resolver:
        return [], f"未配置 {DOH_RESOLVER_ENV}（显式 DoH 需要 HTTPS JSON DNS API）"
    parsed = urllib.parse.urlsplit(resolver)
    try:
        port = parsed.port
    except ValueError:
        return [], "显式 JSON DoH resolver URL 端口无效"
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or port not in {None, 443}
        or parsed.query
        or parsed.fragment
    ):
        return [], "显式 DoH resolver 必须是无凭证、无查询参数的 HTTPS JSON API URL"
    try:
        resolver_answers = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return [], "显式 JSON DoH resolver 自身 DNS 无结果"
    resolver_ips = [answer[4][0] for answer in resolver_answers]
    if not addresses_public(resolver_ips) and not all_fake_ip(resolver_ips):
        return [], "显式 JSON DoH resolver 解析到不允许的地址"
    query = f"{resolver}?name={urllib.parse.quote(hostname, safe='')}&type=A"
    request = urllib.request.Request(query, headers={"accept": "application/dns-json"})
    try:
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(request, timeout=10) as response:
            content_type = str(response.headers.get("Content-Type") or "").split(";", 1)[0].lower()
            raw = response.read(MAX_DOH_RESPONSE_BYTES + 1)
        if len(raw) > MAX_DOH_RESPONSE_BYTES:
            return [], "显式 JSON DoH resolver 响应超过大小限制"
        if content_type == "application/dns-message":
            return [], "显式 DoH resolver 返回 RFC8484 二进制；请配置返回 JSON 的解析端点"
        data = json.loads(raw.decode("utf-8"))
    except OSError:
        return [], "显式 JSON DoH resolver 请求失败"
    except (UnicodeDecodeError, json.JSONDecodeError):
        return [], "显式 DoH resolver 响应不是可解析的 JSON"
    if not isinstance(data, dict):
        return [], "显式 JSON DoH resolver 响应顶层不是对象"
    results: list[str] = []
    for answer in data.get("Answer") or []:
        if not isinstance(answer, dict) or answer.get("type") != 1:
            continue
        value = str(answer.get("data") or "")
        try:
            ipaddress.ip_address(value)
        except ValueError:
            continue
        results.append(value)
    if not results:
        return [], "显式 JSON DoH resolver 未返回 A 记录"
    return results, ""


def doh_public_addresses(hostname: str) -> list[str]:
    """Compatibility wrapper for callers that only need the address list."""
    return doh_public_addresses_with_reason(hostname)[0]


def resolve_public_addresses(hostname: str, port: int = 443) -> tuple[bool, str]:
    """Validate system DNS, using explicit DoH only for an all-fake-IP answer."""
    try:
        answers = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False, "DNS 无结果"
    system_ips = [answer[4][0] for answer in answers]
    if addresses_public(system_ips):
        return True, ""
    if not all_fake_ip(system_ips):
        return False, "解析到非公网地址"
    doh_ips, doh_reason = doh_public_addresses_with_reason(hostname)
    if addresses_public(doh_ips):
        return True, ""
    return False, f"系统 DNS 仅返回 fake-IP；{doh_reason}"
