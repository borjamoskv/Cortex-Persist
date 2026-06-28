#!/usr/bin/env python3
# [C5-REAL] PII Firewall Proof of Concept (PoC)
# Demonstrates that the upgraded Taint Engine successfully detects and blocks PII in multiple obfuscated layers.

import asyncio
import os
from cortex.engine.causal.taint_engine import enforce_taint_check, TaintValidationError

class DummyConnection:
    pass

async def test_payload(name: str, payload: str):
    print(f"\n--- Testing: {name} ---")
    print(f"Payload: {payload}")
    try:
        # Force bypassing token check but keeping Memory Firewall and PII checks active
        os.environ["CORTEX_NO_TAINT_ENFORCE"] = "1"
        
        await enforce_taint_check(conn=DummyConnection(), token=None, content=payload)
        print("Result: ✅ PASS (Payload is clean or allowed)")
    except TaintValidationError as e:
        print(f"Result: ❌ BLOCKED ({e})")

async def main():
    print("=== CORTEX PII FIREWALL PROOF OF CONCEPT (PoC) ===")
    
    # 1. Clean payload
    await test_payload(
        "Clean Payload",
        "This is an allowed exergy-maximized fact with zero leaks."
    )
    
    # 2. Plain PII leak
    await test_payload(
        "Plain Legal Name Leak",
        "Created by Borja Fernandez Angulo."
    )
    
    # 3. Accented / Unicode PII leak
    await test_payload(
        "Accented Unicode Leak",
        "Fact owner: Borja Fernández Angulo."
    )
    
    # 4. Proximity / Co-occurrence leak
    await test_payload(
        "Proximity Leak",
        "Borja published the track. Fernandez was credited as compositor."
    )
    
    # 5. Cyrillic Homoglyph bypass attempt
    # Cyrillic 'a' (\u0430) instead of Latin 'a'
    await test_payload(
        "Cyrillic Homoglyph Bypass Attempt",
        "User identifier: borj\u0430 fernandez"
    )
    
    # 6. URL Encoded bypass attempt
    # "borja" URL-encoded is "%62%6f%72%6a%61"
    await test_payload(
        "URL Encoded Bypass Attempt",
        "url_params=%62%6f%72%6a%61%20%66%65%72%6e%61%6e%64%65%7a"
    )
    
    # 7. Base64 encoded bypass attempt
    # "borja fernandez" in Base64 is "Ym9yamEgZmVybmFuZGV6"
    await test_payload(
        "Base64 Bypass Attempt",
        "encoded_value: Ym9yamEgZmVybmFuZGV6"
    )
    
    # 8. Hex encoded bypass attempt
    # "borja" in hex is "626f726a61", "fernandez" is "6665726e616e64657a"
    await test_payload(
        "Hex Bypass Attempt",
        "0x626f726a616665726e616e64657a"
    )

if __name__ == "__main__":
    asyncio.run(main())
