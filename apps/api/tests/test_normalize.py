import pytest

from apps.api.services.discovery.normalize import normalize_url, platform_for_url, validate_public_url


def test_normalize_removes_tracking_fragments_default_port_and_trailing_slash() -> None:
    assert normalize_url("HTTPS://GitHub.com:443/demo-user/?utm_source=test&b=2&a=1#profile") == "https://github.com/demo-user?a=1&b=2"


def test_platform_uses_known_hostname_mapping() -> None:
    assert platform_for_url("https://www.youtube.com/@demo") == "youtube"
    assert platform_for_url("https://example.org/person") == "example.org"


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com",
        "https://user:password@example.com",
        "https://localhost/profile",
        "http://127.0.0.1/profile",
        "http://[::1]/profile",
    ],
)
def test_public_url_validation_rejects_unsafe_targets(url: str) -> None:
    with pytest.raises(ValueError):
        validate_public_url(url)
