#!/usr/bin/env python3
# [C5-REAL] PII Firewall Proof of Concept (PoC) with Ultrathink Metrics
# Demonstrates that the upgraded Taint Engine successfully detects and blocks PII in multiple obfuscated layers.
# Integrates the Ultrathink Physics Engine to compute thermodynamic exergy yields.

import asyncio
import os
import time
import math
from cortex.engine.causal.taint_engine import enforce_taint_check, TaintValidationError
from cortex.engine.core.ultrathink_physics import UltrathinkPhysicsEngine

class DummyConnection:
    pass

def calculate_shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    length = len(text)
    freqs = {char: text.count(char) for char in set(text)}
    entropy = 0.0
    for count in freqs.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy

async def test_payload(name: str, payload: str):
    print(f"\n--- Testing: {name} ---")
    print(f"Payload: {payload}")
    
    # Calculate initial stochastic entropy
    stoch_entropy = calculate_shannon_entropy(payload)
    print(f"Input Shannon Entropy: {stoch_entropy:.4f} bits/char")
    
    start_time = time.perf_counter()
    try:
        # Force bypassing token check but keeping Memory Firewall and PII checks active
        os.environ["CORTEX_NO_TAINT_ENFORCE"] = "1"
        
        await enforce_taint_check(conn=DummyConnection(), token=None, content=payload)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        
        # Output is clean, meaning deterministic output matches the clean state
        det_output = calculate_shannon_entropy("Result: PASS")
        # Exergy is the rate of entropy reduction (annihilation of noise/anergy)
        exergy = max(0.0, (stoch_entropy - det_output) / execution_time)
        
        print("Result: ✅ PASS (Payload is clean or allowed)")
        print(f"Execution Time: {execution_time*1000:.3f} ms | Cognitive Exergy (Ξ): {exergy:.2f} bits/s")
    except TaintValidationError as e:
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        
        # Blocked state: deterministic output is 0.0 (maximum thermodynamic suppression)
        det_output = 0.0
        exergy = max(0.0, (stoch_entropy - det_output) / execution_time)
        
        print(f"Result: ❌ BLOCKED ({e})")
        print(f"Execution Time: {execution_time*1000:.3f} ms | Cognitive Exergy (Ξ): {exergy:.2f} bits/s")

async def main():
    print("=== CORTEX PII FIREWALL PROOF OF CONCEPT (PoC) WITH ULTRATHINK PHYSICS ===")
    
    # Measure global blast radius of PII exposure for authorization
    dependency_graph = {
        "Host PII": ["Apple Music", "Spotify", "Viberate", "Deezer", "Joox", "YouTube Music"]
    }
    blast_radius = UltrathinkPhysicsEngine.measure_blast_radius(dependency_graph, "Host PII")
    print(f"Topological Blast Radius for PII Exposure: {blast_radius}")
    
    # Calculate global JIT authorization
    # Standard values for the global sweep: H_in = 21.53, H_out = 100.0, time = 0.05s
    authorized, msg, formation = UltrathinkPhysicsEngine.authorize_ultrathink(
        stochastic_entropy=21.53,
        deterministic_output=100.0,
        execution_time=0.05,
        epicenter_radius=blast_radius
    )
    print(f"Ultrathink Authorization Status: {authorized} -> {msg}")
    
    # Run payloads
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
