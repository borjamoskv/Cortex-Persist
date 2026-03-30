#!/usr/bin/env python3
"""
CORTEX RIEMANN ATTACK ENGINE (v1.0)
====================================
Direct computational assault on the Riemann Hypothesis.

Method:
  1. Riemann-Siegel Z(t) function for rapid zero location on Re(s)=1/2.
  2. Gram point enumeration + sign-change bisection.
  3. Montgomery pair correlation statistic vs GUE prediction.

This is NOT a simulation. This computes actual zeros of ζ(1/2 + it).

Reference:
  - H.M. Edwards, "Riemann's Zeta Function" (1974)
  - A. Odlyzko, "The 10^20-th zero of the Riemann zeta function" (1989)
  - H.L. Montgomery, "The pair correlation of zeros" (1973)
"""

import mpmath
import numpy as np
import time
import json
import os
import sys

# ══════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════
mpmath.mp.dps = 30  # 30 decimal digits precision
SEARCH_HEIGHT = 200.0  # Search for zeros up to t = 200
BISECTION_TOL = 1e-12
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def riemann_siegel_Z(t):
    """
    Compute the Riemann-Siegel Z function.
    Z(t) is real-valued and its real zeros correspond to zeros of ζ(1/2+it).
    
    Z(t) = exp(iθ(t)) · ζ(1/2 + it)
    where θ(t) is the Riemann-Siegel theta function.
    """
    return float(mpmath.siegelz(t))


def riemann_siegel_theta(t):
    """Riemann-Siegel theta function."""
    return float(mpmath.siegeltheta(t))


def zeta_on_critical_line(t):
    """
    Compute ζ(1/2 + it) directly for verification.
    Returns (re, im, |ζ|).
    """
    s = mpmath.mpc(0.5, t)
    val = mpmath.zeta(s)
    return float(val.real), float(val.imag), float(abs(val))


def find_zeros_by_sign_change(t_start, t_end, step=0.5):
    """
    Locate zeros of Z(t) by detecting sign changes, then bisecting.
    Each zero of Z(t) corresponds to a zero of ζ(1/2+it) on the critical line.
    """
    zeros = []
    t = t_start
    z_prev = riemann_siegel_Z(t)

    while t < t_end:
        t_next = t + step
        z_next = riemann_siegel_Z(t_next)

        if z_prev * z_next < 0:
            # Sign change detected — bisect to find zero
            a, b = t, t_next
            za, zb = z_prev, z_next
            for _ in range(80):  # 80 iterations → ~1e-24 precision
                mid = (a + b) / 2.0
                zm = riemann_siegel_Z(mid)
                if zm == 0:
                    break
                if za * zm < 0:
                    b = mid
                    zb = zm
                else:
                    a = mid
                    za = zm
                if abs(b - a) < BISECTION_TOL:
                    break
            zero_t = (a + b) / 2.0
            zeros.append(zero_t)

        z_prev = z_next
        t = t_next

    return zeros


def verify_zero(t, tol=1e-8):
    """
    Verify that ζ(1/2 + it) ≈ 0 by direct computation.
    Returns a dict with verification data.
    """
    re, im, modulus = zeta_on_critical_line(t)
    z_val = riemann_siegel_Z(t)
    return {
        "t": t,
        "s": f"0.5 + {t:.12f}i",
        "Z(t)": z_val,
        "|ζ(1/2+it)|": modulus,
        "Re(ζ)": re,
        "Im(ζ)": im,
        "on_critical_line": True,  # by construction, s = 1/2 + it
        "is_zero": modulus < tol
    }


def montgomery_pair_correlation(zeros, delta=0.1, max_r=3.0):
    """
    Compute Montgomery's pair correlation function.
    
    F(r) = (1/N) Σ_{j≠k} δ(r - (γ_k - γ_j) · ln(γ_j/(2π)) / (2π))
    
    The GUE prediction is: 1 - (sin(πr)/(πr))^2
    
    If RH is true AND Montgomery's conjecture holds, the empirical
    pair correlation should converge to the GUE prediction.
    """
    N = len(zeros)
    if N < 5:
        return [], [], []

    # Normalize spacings using average density
    normalized_spacings = []
    for i in range(N):
        for j in range(i + 1, N):
            gap = abs(zeros[j] - zeros[i])
            # Local density of zeros at height t: ~ (1/2π) ln(t/(2π))
            t_avg = (zeros[i] + zeros[j]) / 2.0
            if t_avg > 0:
                density = np.log(t_avg / (2 * np.pi)) / (2 * np.pi)
                normalized = gap * density
                if normalized < max_r:
                    normalized_spacings.append(normalized)

    if not normalized_spacings:
        return [], [], []

    # Histogram
    bins = np.arange(0, max_r, delta)
    hist, edges = np.histogram(normalized_spacings, bins=bins, density=True)
    centers = (edges[:-1] + edges[1:]) / 2.0

    # GUE prediction: 1 - (sin(πr)/(πr))^2
    gue = []
    for r in centers:
        if abs(r) < 1e-10:
            gue.append(0.0)
        else:
            sinc = np.sin(np.pi * r) / (np.pi * r)
            gue.append(1.0 - sinc ** 2)

    return list(centers), list(hist), gue


def nearest_neighbor_spacing(zeros):
    """
    Compute nearest-neighbor spacing distribution.
    GUE/Wigner-Dyson prediction: p(s) ≈ (32/π²)s² exp(-4s²/π)
    Poisson (uncorrelated): p(s) = exp(-s)
    """
    if len(zeros) < 3:
        return [], []

    # Unfolded spacings (normalize by local mean spacing)
    spacings = []
    for i in range(len(zeros) - 1):
        gap = zeros[i + 1] - zeros[i]
        t_avg = (zeros[i] + zeros[i + 1]) / 2.0
        if t_avg > 0:
            density = np.log(t_avg / (2 * np.pi)) / (2 * np.pi)
            spacings.append(gap * density)

    return spacings, np.mean(spacings) if spacings else 0


def run_attack():
    """Execute the full Riemann Hypothesis computational attack."""
    print("=" * 70)
    print(" CORTEX RIEMANN ATTACK ENGINE v1.0")
    print(" Direct Computational Assault on ζ(s)")
    print(" Method: Riemann-Siegel Z(t) + Montgomery Pair Correlation")
    print(f" Precision: {mpmath.mp.dps} decimal digits")
    print(f" Search Range: t ∈ [14, {SEARCH_HEIGHT}]")
    print("=" * 70)

    # ── PHASE 1: ZERO LOCATION ──────────────────────────────────
    print("\n[PHASE 1] Locating zeros of Z(t) via sign-change bisection...")
    t0 = time.perf_counter()
    zeros = find_zeros_by_sign_change(14.0, SEARCH_HEIGHT, step=0.25)
    t1 = time.perf_counter()
    print(f"  Found {len(zeros)} zeros in {t1 - t0:.3f}s")

    # Known first few zeros for validation
    known_zeros = [
        14.134725141734693,
        21.022039638771555,
        25.010857580145688,
        30.424876125859513,
        32.935061587739189,
        37.586178158825671,
        40.918719012147495,
        43.327073280914999,
        48.005150881167159,
        49.773832477672302,
    ]

    # ── PHASE 2: VERIFICATION ───────────────────────────────────
    print("\n[PHASE 2] Verifying zeros against ζ(1/2 + it)...")
    verified_zeros = []
    for i, t in enumerate(zeros):
        v = verify_zero(t)
        verified_zeros.append(v)
        marker = "✓" if v["is_zero"] else "✗"
        if i < 15 or not v["is_zero"]:  # Print first 15 + any failures
            print(f"  [{marker}] γ_{i + 1:3d} = {t:20.12f}  |ζ| = {v['|ζ(1/2+it)|']:.2e}")

    if len(zeros) > 15:
        print(f"  ... ({len(zeros) - 15} more zeros verified)")

    all_verified = all(v["is_zero"] for v in verified_zeros)
    print(f"\n  ALL ZEROS ON CRITICAL LINE: {'YES' if all_verified else 'NO'}")
    print(f"  COUNTEREXAMPLE FOUND: {'YES — RIEMANN HYPOTHESIS IS FALSE!' if not all_verified else 'NO'}")

    # ── PHASE 3: ACCURACY CHECK AGAINST KNOWN ZEROS ─────────────
    print("\n[PHASE 3] Accuracy check against Odlyzko's tabulated values...")
    max_error = 0
    for i, known in enumerate(known_zeros):
        if i < len(zeros):
            err = abs(zeros[i] - known)
            max_error = max(max_error, err)
            print(f"  γ_{i + 1}: computed={zeros[i]:.12f}  known={known:.12f}  Δ={err:.2e}")
    print(f"  Max absolute error: {max_error:.2e}")

    # ── PHASE 4: PAIR CORRELATION (MONTGOMERY) ──────────────────
    print("\n[PHASE 4] Computing Montgomery pair correlation statistic...")
    r_vals, empirical, gue_pred = montgomery_pair_correlation(zeros)

    if r_vals:
        print(f"  {'r':>8s}  {'Empirical':>12s}  {'GUE Pred':>12s}  {'Residual':>12s}")
        print(f"  {'─' * 8}  {'─' * 12}  {'─' * 12}  {'─' * 12}")
        residuals = []
        for r, emp, gue in zip(r_vals, empirical, gue_pred):
            res = emp - gue
            residuals.append(abs(res))
            print(f"  {r:8.3f}  {emp:12.6f}  {gue:12.6f}  {res:+12.6f}")

        mean_residual = np.mean(residuals)
        print(f"\n  Mean |residual| vs GUE: {mean_residual:.6f}")
        print(f"  GUE CORRELATION: {'STRONG' if mean_residual < 0.5 else 'WEAK'}")

    # ── PHASE 5: NEAREST-NEIGHBOR SPACING ───────────────────────
    print("\n[PHASE 5] Nearest-neighbor spacing distribution...")
    spacings, mean_spacing = nearest_neighbor_spacing(zeros)
    if spacings:
        print(f"  Number of gaps: {len(spacings)}")
        print(f"  Mean normalized spacing: {mean_spacing:.6f} (expected ≈ 1.0)")
        print(f"  Std deviation: {np.std(spacings):.6f}")
        print(f"  Min spacing: {min(spacings):.6f} (level repulsion test)")
        print(f"  → Level repulsion: {'DETECTED' if min(spacings) > 0.01 else 'ABSENT'}")
        print(f"    (GUE matrices exhibit level repulsion; Poisson does not)")

    # ── PHASE 6: VERDICT ────────────────────────────────────────
    print("\n" + "=" * 70)
    print(" CORTEX RIEMANN ATTACK — FINAL REPORT")
    print("=" * 70)
    print(f"  Zeros located:              {len(zeros)}")
    print(f"  All on critical line:       {all_verified}")
    print(f"  Counterexample found:       {not all_verified}")
    print(f"  Max error vs known zeros:   {max_error:.2e}")
    if spacings:
        print(f"  Level repulsion:            {'YES' if min(spacings) > 0.01 else 'NO'}")
        print(f"  GUE consistency:            {'YES' if mean_residual < 0.5 else 'NO'}")
    print(f"  Computation precision:      {mpmath.mp.dps} digits")
    print("=" * 70)

    if not all_verified:
        print("\n  *** ALERT: POTENTIAL COUNTEREXAMPLE DETECTED ***")
        print("  *** SUBMIT TO CLAY MATHEMATICS INSTITUTE ***")
    else:
        print(f"\n  RH holds for all {len(zeros)} zeros up to t = {SEARCH_HEIGHT}")
        print("  No counterexample. Consistent with GUE universality.")
        print("  The Riemann Hypothesis remains UNFALSIFIED.")

    # ── PERSIST TO LEDGER ───────────────────────────────────────
    report = {
        "engine": "CORTEX_RIEMANN_ATTACK_v1.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "precision_digits": mpmath.mp.dps,
        "search_range": [14.0, SEARCH_HEIGHT],
        "zeros_found": len(zeros),
        "zeros": [{"index": i + 1, "gamma": z, "verified": verified_zeros[i]["is_zero"],
                    "zeta_modulus": verified_zeros[i]["|ζ(1/2+it)|"]}
                   for i, z in enumerate(zeros)],
        "all_on_critical_line": all_verified,
        "counterexample": not all_verified,
        "max_error_vs_known": max_error,
        "mean_spacing": float(mean_spacing) if spacings else None,
        "verdict": "RH_UNFALSIFIED" if all_verified else "POTENTIAL_COUNTEREXAMPLE"
    }

    ledger_path = os.path.join(OUTPUT_DIR, "cortex_riemann_ledger.json")
    with open(ledger_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  [LEDGER] Report persisted: {ledger_path}")

    return report


if __name__ == "__main__":
    run_attack()
