from __future__ import annotations

from cortex.search.utils import _decrypt_row_content


class _FailingEncrypter:
    def decrypt_str(self, content: str, tenant_id: str = "default") -> str:
        raise ValueError("wrong key")


def test_decrypt_row_content_returns_empty_on_ciphertext_failure() -> None:
    encrypted = "v6_aesgcm:opaque-ciphertext"
    assert _decrypt_row_content(encrypted, "tenant-a", _FailingEncrypter()) == ""
