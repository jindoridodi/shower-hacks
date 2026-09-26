"""URL validation and canonicalization for public candidate sources."""

from __future__ import annotations

import ipaddress
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMETERS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src"}
HOST_ALIASES = {
    "m.instagram.com": "instagram.com",
    "mobile.twitter.com": "x.com",
    "www.youtube.com": "youtube.com",
}
PLATFORM_HOSTS = {
    "github.com": "github",
    "linkedin.com": "linkedin",
    "instagram.com": "instagram",
    "tiktok.com": "tiktok",
    "youtube.com": "youtube",
    "medium.com": "medium",
    "substack.com": "substack",
    "x.com": "x",
}


def normalize_username(value: str) -> str:
    """Validate a discovery username and return its stable storage key."""

    username = value.strip()
    if not username:
        raise ValueError("username must not be empty")
    if len(username) > 64:
        raise ValueError("username queries must be at most 64 characters")
    if not all(character.isalnum() or character in "._-" for character in username):
        raise ValueError("username contains unsupported characters")
    return username.casefold()


def _is_blocked_ip(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
        )
    )


def validate_public_url(value: str) -> None:
    """Reject malformed, credentialed, local, and non-public URL literals."""

    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("URL scheme must be http or https")
    if not parsed.hostname:
        raise ValueError("URL must include a hostname")
    if parsed.username or parsed.password:
        raise ValueError("URL credentials are not allowed")
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("URL port is invalid") from error
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("URL port is invalid")
    host = parsed.hostname.lower().rstrip(".")
    if host == "localhost" or host.endswith(".localhost") or _is_blocked_ip(host):
        raise ValueError("local and private URL targets are not allowed")


def normalize_url(value: str) -> str:
    """Return a stable canonical URL after public-target validation."""

    validate_public_url(value)
    parsed = urlsplit(value)
    scheme = parsed.scheme.lower()
    host = HOST_ALIASES.get(parsed.hostname.lower().rstrip("."), parsed.hostname.lower().rstrip("."))
    try:
        port = parsed.port
    except ValueError as error:  # pragma: no cover - guarded by validate_public_url
        raise ValueError("URL port is invalid") from error
    include_port = port is not None and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443))
    netloc = host if not include_port else f"{host}:{port}"
    path = parsed.path.rstrip("/") if parsed.path not in {"", "/"} else ""
    pairs = [
        (key, item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_PARAMETERS
    ]
    query = urlencode(sorted(pairs))
    return urlunsplit((scheme, netloc, path, query, ""))


def canonical_key(value: str) -> str:
    """Canonical identity key used for candidate deduplication."""

    return normalize_url(value)


def platform_for_url(value: str, fallback: str | None = None) -> str:
    """Resolve a stable platform identifier from a normalized URL."""

    host = urlsplit(normalize_url(value)).hostname or ""
    for known_host, platform in PLATFORM_HOSTS.items():
        if host == known_host or host.endswith(f".{known_host}"):
            return platform
    return fallback or host
