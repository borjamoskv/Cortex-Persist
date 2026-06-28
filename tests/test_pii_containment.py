# [C5-REAL] Exergy-Maximized
"""
Verification tests for Host Identity Containment (Epoch 13).
"""
import pytest

from cortex.engine.causal.taint_engine import enforce_taint_check, TaintValidationError


@pytest.mark.asyncio
async def test_pii_clean_payload_passes():
    """Verify that a clean payload does not raise any PII exceptions."""
    # Should not raise
    await enforce_taint_check(conn=None, token=None, content="Clean payload representing factual state.")


@pytest.mark.asyncio
async def test_pii_literal_leak_blocked():
    """Verify that literal name strings are strictly blocked."""
    with pytest.raises(TaintValidationError) as excinfo:
        await enforce_taint_check(conn=None, token=None, content="This fact belongs to borja fernandez angulo.")
    assert "Host Identity PII" in str(excinfo.value)


@pytest.mark.asyncio
async def test_pii_accented_leak_blocked():
    """Verify that unicode variations with diacritics / accents are blocked."""
    with pytest.raises(TaintValidationError):
        await enforce_taint_check(conn=None, token=None, content="Fact by Borja Fernández Angulo.")


@pytest.mark.asyncio
async def test_pii_obfuscated_leak_blocked():
    """Verify that obfuscated strings like dashes or dots are blocked."""
    with pytest.raises(TaintValidationError):
        await enforce_taint_check(conn=None, token=None, content="user: borja-fernandez-angulo")
        
    with pytest.raises(TaintValidationError):
        await enforce_taint_check(conn=None, token=None, content="path: /users/borja_fernandez_angulo/data")


@pytest.mark.asyncio
async def test_pii_proximity_leak_blocked():
    """Verify that co-occurrence of name tokens is blocked."""
    with pytest.raises(TaintValidationError):
        await enforce_taint_check(
            conn=None, 
            token=None, 
            content="Borja went to the store. Fernandez was also there."
        )


@pytest.mark.asyncio
async def test_pii_homoglyph_leak_blocked():
    """Verify that Cyrillic and Greek lookalike character bypasses are blocked."""
    # Cyrillic 'а' (u0430) instead of Latin 'a'
    with pytest.raises(TaintValidationError):
        await enforce_taint_check(conn=None, token=None, content="borj\u0430 fernandez")
        
    # Greek 'ο' (u03bf) instead of Latin 'o'
    with pytest.raises(TaintValidationError):
        await enforce_taint_check(conn=None, token=None, content="b\u03bfrja fernandez")


@pytest.mark.asyncio
async def test_pii_url_encoded_leak_blocked():
    """Verify that URL encoded PII is detected and blocked."""
    # "borja" URL-encoded is "%62%6f%72%6a%61"
    with pytest.raises(TaintValidationError):
        await enforce_taint_check(conn=None, token=None, content="payload=%62%6f%72%6a%61%20%66%65%72%6e%61%6e%64%65%7a")


@pytest.mark.asyncio
async def test_pii_base64_leak_blocked():
    """Verify that Base64 encoded PII is detected and blocked."""
    # "borja fernandez" in Base64 is "Ym9yamEgZmVybmFuZGV6"
    with pytest.raises(TaintValidationError):
        await enforce_taint_check(conn=None, token=None, content="data: Ym9yamEgZmVybmFuZGV6")


@pytest.mark.asyncio
async def test_pii_hex_leak_blocked():
    """Verify that hex encoded PII is detected and blocked."""
    # "borja" in hex is "626f726a61", "fernandez" is "6665726e616e64657a"
    with pytest.raises(TaintValidationError):
        await enforce_taint_check(conn=None, token=None, content="0x626f726a616665726e616e64657a")

