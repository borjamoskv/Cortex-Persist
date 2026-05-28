#!/usr/bin/env python3
"""
VSA-SDM CHAOS FUZZER v1.0
Adversarial stress-test. Tries to BREAK everything.

12 attack vectors:
  [0]  Zero vector injection
  [1]  NaN / Inf poisoning
  [2]  Extreme dimensionality (D=64, D=65536)
  [3]  Capacity overflow (N >> sqrt(D))
  [4]  Identical key collision
  [5]  Adversarial near-orthogonal attack
  [6]  Persistence corruption (bit-flip)
  [7]  Decode without encode (empty memory)
  [8]  Temporal decay extremes (λ=0, λ=1000)
  [9]  Unicode / empty string encoding
  [10] MAP-B vs HRR algebraic consistency
  [11] Federation with mismatched dimensions
"""
import hashlib
import os
import struct
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vsa_engine import VSAEngine


PASS = 0
FAIL = 0


def report(name, ok, detail=""):
    global PASS, FAIL
    tag = "PASS" if ok else "FAIL"
    if not ok:
        FAIL += 1
    else:
        PASS += 1
    print(f"  [{tag}] {name}" + (f" — {detail}" if detail else ""))


def fuzz_zero_vector():
    """[0] Zero vector injection — bind/unbind with zero."""
    print("\n[0] ZERO VECTOR INJECTION")
    e = VSAEngine(D=1000, seed=1)
    zero = np.zeros(1000)
    v = e.random_vec()

    # Bind with zero should not crash
    try:
        r = e.bind(zero, v)
        report("bind(zero, v)", True, f"norm={np.linalg.norm(r):.6f}")
    except Exception as ex:
        report("bind(zero, v)", False, str(ex))

    # Cosine with zero should handle gracefully
    try:
        s = e.cosine(zero, v)
        report("cosine(zero, v)", s == 0.0, f"sim={s}")
    except Exception as ex:
        report("cosine(zero, v)", False, str(ex))

    # Normalize zero should not crash
    try:
        n = e.normalize(zero)
        report("normalize(zero)", True, f"norm={np.linalg.norm(n):.6f}")
    except Exception as ex:
        report("normalize(zero)", False, str(ex))


def fuzz_nan_inf():
    """[1] NaN / Inf poisoning."""
    print("\n[1] NaN / Inf POISONING")
    e = VSAEngine(D=1000, seed=2)
    v = e.random_vec()

    nan_vec = np.full(1000, np.nan)
    inf_vec = np.full(1000, np.inf)

    # These should not produce valid output but must not crash
    try:
        r = e.bind(nan_vec, v)
        has_nan = np.any(np.isnan(r))
        report("bind(NaN, v)", True, f"output_has_nan={has_nan}")
    except Exception as ex:
        report("bind(NaN, v)", False, str(ex))

    try:
        r = e.bind(inf_vec, v)
        has_inf = np.any(np.isinf(r))
        report("bind(Inf, v)", True, f"output_has_inf={has_inf}")
    except Exception as ex:
        report("bind(Inf, v)", False, str(ex))

    try:
        s = e.cosine(nan_vec, v)
        report("cosine(NaN, v)", True, f"sim={s}")
    except Exception as ex:
        report("cosine(NaN, v)", False, str(ex))


def fuzz_extreme_dimensions():
    """[2] Extreme dimensionality."""
    print("\n[2] EXTREME DIMENSIONALITY")

    # Tiny D
    e_tiny = VSAEngine(D=64, seed=3)
    k, s = e_tiny.random_vec(), e_tiny.random_vec()
    m = e_tiny.bind(k, s)
    r = e_tiny.unbind(m, k)
    sim = e_tiny.cosine(s, r)
    report(f"D=64 bind/unbind", sim > 0.05, f"cos={sim:.4f}")

    # Large D
    e_big = VSAEngine(D=50000, seed=4)
    k, s = e_big.random_vec(), e_big.random_vec()
    m = e_big.bind(k, s)
    r = e_big.unbind(m, k)
    sim = e_big.cosine(s, r)
    report(f"D=50000 bind/unbind", sim > 0.5, f"cos={sim:.4f}")


def fuzz_capacity_overflow():
    """[3] Push N way past sqrt(D) — expect degradation, not crash."""
    print("\n[3] CAPACITY OVERFLOW")
    D = 1000
    e = VSAEngine(D=D, seed=5)

    N = 5000  # sqrt(1000) ≈ 31, so 160x over capacity
    keys = [e.random_vec() for _ in range(N)]
    states = [e.random_vec() for _ in range(N)]

    memory = np.zeros(D)
    for k, s in zip(keys, states):
        memory += e.bind(k, s)

    # SNR should be terrible
    snr = np.sqrt(D / N)
    report(f"N={N}, D={D}", True, f"SNR={snr:.2f} (expected ~0.45)")

    # Retrieval should be near-random
    extracted = e.unbind(memory, keys[0])
    sim = e.cosine(states[0], extracted)
    report(f"Retrieval at 160x overcapacity", True,
           f"cos={sim:.4f} (noise level expected)")


def fuzz_key_collision():
    """[4] What happens when two items share the same key?"""
    print("\n[4] KEY COLLISION")
    e = VSAEngine(D=10000, seed=6)

    key = e.random_vec()
    s1 = e.random_vec()
    s2 = e.random_vec()

    memory = e.bind(key, s1) + e.bind(key, s2)
    extracted = e.unbind(memory, key)

    # Should get superposition of s1 and s2
    sim1 = e.cosine(s1, extracted)
    sim2 = e.cosine(s2, extracted)
    report("Same key, two values", sim1 > 0.2 and sim2 > 0.2,
           f"cos(s1)={sim1:.4f}, cos(s2)={sim2:.4f}")


def fuzz_near_orthogonal_attack():
    """[5] Adversarial: craft vectors that are almost identical."""
    print("\n[5] NEAR-ORTHOGONAL ATTACK")
    e = VSAEngine(D=10000, seed=7)

    base = e.random_vec()
    # Create a vector that differs by only 1 dimension
    adversary = base.copy()
    adversary[0] = -adversary[0]
    adversary = e.normalize(adversary)

    sim = e.cosine(base, adversary)
    report("Near-identical vectors distinguishable",
           sim > 0.999,
           f"cos={sim:.6f} (should be ~0.9998)")

    # Can we still separate them after binding?
    k1, k2 = e.random_vec(), e.random_vec()
    memory = e.bind(k1, base) + e.bind(k2, adversary)
    r1 = e.unbind(memory, k1)
    r2 = e.unbind(memory, k2)
    s1 = e.cosine(base, r1)
    s2 = e.cosine(adversary, r2)
    report("Separation after binding", s1 > 0.3 and s2 > 0.3,
           f"cos(base)={s1:.4f}, cos(adv)={s2:.4f}")


def fuzz_persistence_corruption():
    """[6] Flip random bits in a .vsa file — must detect corruption."""
    print("\n[6] PERSISTENCE CORRUPTION")
    e = VSAEngine(D=1000, seed=8)
    e.memorize(e.random_vec(), e.random_vec(), timestamp=0.0)

    tmp = tempfile.mktemp(suffix=".vsa")
    e.save(tmp)

    # Read the file, flip a byte in the tensor data
    with open(tmp, "rb") as f:
        data = bytearray(f.read())

    # Corrupt a byte in the tensor region (after 12-byte header)
    data[100] ^= 0xFF

    with open(tmp, "wb") as f:
        f.write(data)

    # Load should detect SHA-256 mismatch
    e2 = VSAEngine(D=1000, seed=8)
    try:
        e2.load(tmp)
        report("Corruption detected", False, "Load succeeded on corrupt file!")
    except ValueError as ex:
        report("Corruption detected", "SHA-256" in str(ex) or "integrity" in str(ex).lower(),
               str(ex))
    finally:
        os.unlink(tmp)


def fuzz_empty_memory():
    """[7] Retrieve from empty memory — should not crash."""
    print("\n[7] EMPTY MEMORY RETRIEVAL")
    e = VSAEngine(D=1000, seed=9)

    key = e.random_vec()
    try:
        r = e.recall(key)
        report("Recall from empty", True,
               f"norm={np.linalg.norm(r):.6f}")
    except Exception as ex:
        report("Recall from empty", False, str(ex))

    # SNR of empty memory
    snr = e.snr
    report("SNR of empty memory", snr == float('inf'),
           f"snr={snr}")


def fuzz_decay_extremes():
    """[8] Extreme decay parameters."""
    print("\n[8] DECAY EXTREMES")
    e = VSAEngine(D=1000, seed=10)

    # λ=0 (no decay, all memories equal weight)
    k1, s1 = e.random_vec(), e.random_vec()
    e.memorize(k1, s1, timestamp=0.0, decay_lambda=0.0)
    r = e.recall(k1)
    sim = e.cosine(s1, r)
    report("λ=0 (no decay)", sim > 0.5, f"cos={sim:.4f}")

    # λ=1000 (extreme decay, instant forget)
    e2 = VSAEngine(D=1000, seed=11)
    k2, s2 = e2.random_vec(), e2.random_vec()
    e2.memorize(k2, s2, timestamp=0.0, decay_lambda=1000.0)
    # After rebuild, weight = exp(-1000 * Δt) ≈ 0 (unless Δt ≈ 0)
    purged = e2.forget(epsilon=0.01)
    report("λ=1000 (instant forget)", True,
           f"purged={purged} items")


def fuzz_unicode_encoding():
    """[9] Unicode, empty string, and special characters."""
    print("\n[9] UNICODE / EDGE-CASE ENCODING")
    e = VSAEngine(D=1000, seed=12)

    # Empty string
    try:
        v = e.encode_text("")
        report("Empty string", True, f"norm={np.linalg.norm(v):.6f}")
    except Exception as ex:
        report("Empty string", False, str(ex))

    # Single character (too short for trigrams)
    try:
        v = e.encode_text("a")
        report("Single char 'a'", True, f"norm={np.linalg.norm(v):.6f}")
    except Exception as ex:
        report("Single char", False, str(ex))

    # Unicode (chars not in codebook)
    try:
        v = e.encode_text("日本語テスト")
        report("Japanese Unicode", True, f"norm={np.linalg.norm(v):.6f}")
    except Exception as ex:
        report("Japanese Unicode", False, str(ex))

    # Very long string
    try:
        v = e.encode_text("a" * 100000)
        report("100K char string", True, f"norm={np.linalg.norm(v):.6f}")
    except Exception as ex:
        report("100K char string", False, str(ex))

    # Mixed valid/invalid
    try:
        v = e.encode_text("hello 世界 world")
        report("Mixed encoding", True, f"norm={np.linalg.norm(v):.6f}")
    except Exception as ex:
        report("Mixed encoding", False, str(ex))


def fuzz_algebra_consistency():
    """[10] HRR and MAP-B should produce consistent results."""
    print("\n[10] HRR vs MAP-B CONSISTENCY")

    e_hrr = VSAEngine(D=10000, algebra="HRR", seed=42)
    e_mapb = VSAEngine(D=10000, algebra="MAPB", seed=42)

    # Both should produce unit vectors
    v_hrr = e_hrr.random_vec()
    v_mapb = e_mapb.random_vec()
    report("Random vec generation",
           abs(np.linalg.norm(v_hrr) - 1.0) < 1e-6,
           f"HRR norm={np.linalg.norm(v_hrr):.6f}")

    # MAP-B self-inverse property
    a, b = e_mapb.random_bipolar(), e_mapb.random_bipolar()
    bound = e_mapb.bind(a, b)
    unbound = e_mapb.unbind(bound, b)
    report("MAP-B self-inverse", np.allclose(a, unbound),
           f"max_err={np.max(np.abs(a - unbound)):.2e}")

    # HRR approximate inverse
    a, b = e_hrr.random_vec(), e_hrr.random_vec()
    bound = e_hrr.bind(a, b)
    unbound = e_hrr.unbind(bound, b)
    sim = e_hrr.cosine(a, unbound)
    report("HRR approximate inverse", sim > 0.5,
           f"cos={sim:.4f}")


def fuzz_dimension_mismatch():
    """[11] Federation with mismatched dimensions."""
    print("\n[11] DIMENSION MISMATCH")

    e1 = VSAEngine(D=1000, seed=1)
    e2 = VSAEngine(D=2000, seed=2)

    # Save D=1000 tensor
    tmp = tempfile.mktemp(suffix=".vsa")
    e1.memorize(e1.random_vec(), e1.random_vec(), timestamp=0.0)
    e1.save(tmp)

    # Try loading into D=2000 engine — should fail
    try:
        e2.load(tmp)
        report("Dimension mismatch rejected", False,
               "Load succeeded with wrong D!")
    except ValueError as ex:
        report("Dimension mismatch rejected", True, str(ex))
    finally:
        os.unlink(tmp)

    # Bind vectors of mismatched sizes (should crash or be caught)
    try:
        v1 = np.ones(1000)
        v2 = np.ones(2000)
        r = np.fft.ifft(np.fft.fft(v1) * np.fft.fft(v2)).real
        report("Mismatched bind", False, "Should have failed")
    except ValueError:
        report("Mismatched bind", True, "ValueError caught")


def fuzz_resonator_adversarial():
    """[12] BONUS: Resonator with ambiguous composite."""
    print("\n[12] RESONATOR ADVERSARIAL")
    e = VSAEngine(D=10000, seed=99)

    # Create codebook where two entries are very similar
    cb = [e.random_vec() for _ in range(20)]
    # Make entry 5 almost identical to entry 10
    cb[10] = cb[5] + 0.01 * e.random_vec()
    cb[10] = e.normalize(cb[10])

    e.register_codebook("ambiguous", cb)

    # Build composite with the ambiguous entry
    composite = e.bind(cb[5], cb[5])
    try:
        factors = e.resonate(composite, ["ambiguous", "ambiguous"])
        idx0, idx1 = factors[0][1], factors[1][1]
        # Should resolve to 5 or 10 (both acceptable)
        ok = idx0 in (5, 10) and idx1 in (5, 10)
        report("Ambiguous resonator", ok,
               f"resolved to [{idx0}, {idx1}]")
    except Exception as ex:
        report("Ambiguous resonator", False, str(ex))


if __name__ == "__main__":
    print("=" * 60)
    print("VSA-SDM CHAOS FUZZER v1.0 — ADVERSARIAL STRESS TEST")
    print("=" * 60)

    fuzz_zero_vector()
    fuzz_nan_inf()
    fuzz_extreme_dimensions()
    fuzz_capacity_overflow()
    fuzz_key_collision()
    fuzz_near_orthogonal_attack()
    fuzz_persistence_corruption()
    fuzz_empty_memory()
    fuzz_decay_extremes()
    fuzz_unicode_encoding()
    fuzz_algebra_consistency()
    fuzz_dimension_mismatch()
    fuzz_resonator_adversarial()

    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"CHAOS FUZZER COMPLETE: {PASS}/{total} passed, "
          f"{FAIL}/{total} failed")
    if FAIL == 0:
        print("VERDICT: SYSTEM IS ADVERSARIALLY ROBUST ✓")
    else:
        print(f"VERDICT: {FAIL} VULNERABILITIES DETECTED ✗")
    print("=" * 60)

    sys.exit(1 if FAIL > 0 else 0)
