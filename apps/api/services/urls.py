"""Canonical public URL normalization.

Rules, applied together:
- require an http or https URL with a host and without username or password
- lowercase the scheme and host, and encode the host as ASCII (IDNA)
- drop fragments and default ports (80 for http, 443 for https)
- collapse ".", "..", and repeated slashes in the path
- keep a trailing slash only for the root path
- percent-decode path and query components, then encode them again
- sort query parameters by key, then value
"""

from __future__ import annotations

import ipaddress
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit


class InvalidURL(ValueError):
    """The URL cannot be stored as a public source address."""


def canonicalize_url(url: str) -> str:
    raw = url.strip()
    if not raw:
        raise InvalidURL("URL is required")
    if any(character.isspace() for character in raw):
        raise InvalidURL("URL must not contain whitespace")

    try:
        parsed = urlsplit(raw)
        scheme = parsed.scheme.lower()
        username = parsed.username
        password = parsed.password
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise InvalidURL("URL is not valid") from exc
    if scheme not in {"http", "https"}:
        raise InvalidURL("Only http and https URLs can be stored")
    if username is not None or password is not None:
        raise InvalidURL("URL must not include username or password")
    if not host:
        raise InvalidURL("URL must include a host")

    ascii_host = _ascii_host(host)
    if port is None or _is_default_port(scheme, port):
        port_suffix = ""
    else:
        port_suffix = f":{port}"
    netloc_host = f"[{ascii_host}]" if ":" in ascii_host else ascii_host
    query = _canonical_query(parsed.query)
    return urlunsplit((scheme, f"{netloc_host}{port_suffix}", _canonical_path(parsed.path), query, ""))


def _is_default_port(scheme: str, port: int) -> bool:
    return (scheme == "http" and port == 80) or (scheme == "https" and port == 443)


def _ascii_host(host: str) -> str:
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass
    try:
        return host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise InvalidURL("URL host is not valid") from exc


def _canonical_path(path: str) -> str:
    segments: list[str] = []
    for raw_segment in path.split("/"):
        segment = unquote(raw_segment)
        if segment in {"", "."}:
            continue
        if segment == "..":
            if segments:
                segments.pop()
            continue
        segments.append(quote(segment, safe="-._~"))
    if not segments:
        return "/"
    return "/" + "/".join(segments)


def _canonical_query(query: str) -> str:
    pairs = [
        (unquote(key), unquote(value))
        for key, value in parse_qsl(query, keep_blank_values=True)
    ]
    return urlencode(sorted(pairs), quote_via=_quote_component)


def _quote_component(
    value: str,
    safe: str = "",
    encoding: str | None = None,
    errors: str | None = None,
) -> str:
    del safe, encoding, errors
    return quote(str(value), safe="-._~")
