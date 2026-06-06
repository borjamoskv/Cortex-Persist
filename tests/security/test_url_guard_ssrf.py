# [C5-REAL] Exergy-Maximized
import pytest

from cortex.guards.url_guard import SafeTransport


def test_url_guard_blocks_metadata_ip():
    """Verify that cloud metadata IPs are blocked (Axiom Ω₁)."""
    unsafe_urls = [
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://127.0.0.1:8000/admin",
        "http://localhost:5000",
        "http://10.0.0.1/sensitive",
        "http://192.168.1.1/config",
    ]

    for url in unsafe_urls:
        with pytest.raises(ValueError, match="Sovereign URLGuard blocked"):
            SafeTransport.validate(url)


def test_url_guard_allows_safe_url():
    """Verify that public legitimate URLs are allowed."""
    safe_urls = [
        "https://google.com",
        "https://github.com/borjamoskv/Cortex-Persist",
        "http://example.com/api/v1/health",
    ]

    for url in safe_urls:
        # Should not raise
        SafeTransport.validate(url)


def test_url_guard_blocks_encoded_null():
    """Verify that null-byte injection is blocked."""
    url = "http://169.254.169.254\0.example.com"
    with pytest.raises(ValueError, match="Sovereign URLGuard blocked"):
        SafeTransport.validate(url)
