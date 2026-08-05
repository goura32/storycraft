"""Private-network endpoint validation and one-call DNS pinning."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request

from .series_contracts import ContractError, EndpointResolutionError


def is_private_lan_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if address.version == 4:
        return any(address in network for network in (
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16"),
        ))
    return address in ipaddress.ip_network("fc00::/7")


def resolve_allowed_addresses(host: str, port: int | None = None) -> tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...]:
    """Resolve a host and reject every result outside loopback/private LAN."""
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            addresses = {
                ipaddress.ip_address(entry[4][0])
                for entry in socket.getaddrinfo(host, port or 0, type=socket.SOCK_STREAM)
            }
        except (OSError, ValueError) as exc:
            raise EndpointResolutionError("endpointのhostを一時的に解決できません") from exc
    if not addresses or any(not (address.is_loopback or is_private_lan_address(address)) for address in addresses):
        raise ContractError("endpointはloopbackまたはプライベートLANのhostだけ許可されます")
    return tuple(sorted(addresses, key=lambda value: (value.version, int(value))))


def pinned_http_request(request: Request) -> Request:
    """Replace a hostname with the validated address for this physical request.

    The original Host header is retained so virtual-hosted local services still
    work.  Canonical Storycraft settings only permit HTTP, but non-HTTP callers
    are rejected here rather than silently bypassing the pinning guarantee.
    """
    try:
        parsed = urlsplit(request.full_url)
        explicit_port = parsed.port
    except (TypeError, ValueError) as exc:
        raise ContractError("provider endpointのURLが不正です") from exc
    if explicit_port == 0:
        raise ContractError("provider endpointのportは1以上でなければなりません")
    port = explicit_port if explicit_port is not None else 80
    if parsed.scheme != "http" or not parsed.hostname:
        raise ContractError("provider endpointはHTTP URLが必要です")
    if parsed.username is not None or parsed.password is not None:
        raise ContractError("provider endpointへcredentialを埋め込めません")
    addresses = resolve_allowed_addresses(parsed.hostname, port)
    address = str(addresses[0])
    host_literal = f"[{address}]" if ":" in address else address
    netloc = host_literal if parsed.port is None else f"{host_literal}:{port}"
    pinned_url = urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
    headers = dict(request.header_items())
    headers["Host"] = parsed.netloc
    return Request(
        pinned_url,
        data=request.data,
        headers=headers,
        origin_req_host=request.origin_req_host,
        unverifiable=request.unverifiable,
        method=request.get_method(),
    )
