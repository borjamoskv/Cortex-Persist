"""Integration tests for BiologicallyModulatedEngine + ActiveInferenceEngine.

Tests verify that hormonal states produce *relative shifts* in EFE scores
and action selection via carefully designed scenarios.

Key insight: In EFE, the "risk" term is KL[Q(s'|a) || preferences],
measuring goal-divergence, NOT volatility. So we design scenarios where:
- SAFE has low KL (goal-aligned) but HIGH ambiguity (noisy observations)
- RISK has high KL (goal-divergent) but LOW ambiguity (clear observations)
This creates a tension where risk_weight and ambiguity_weight pull in
opposite directions, enabling hormonal modulation to flip behavior.

Phase 4.1: Tests for exponential decay, receptor competition, tolerance,
substance cap, to_dict with substances, and __repr__.
"""

import unittest

import numpy as np

from cortex.sovereign.bio_idc import BiologicallyModulatedEngine
from cortex.sovereign.endocrine import (
    DigitalEndocrine,
    Substance,
    MAX_ACTIVE_SUBSTANCES,
)
from idc_core import ActiveInferenceEngine


def _build_conflict_scenario():
    """Build scenario where risk and ambiguity pull oppositely.

    2 actions, 2 states.
    - STAY (0): goal-aligned (low KL) but ambiguous observations
    - VENTURE (1): goal-divergent (high KL) but clear observations

    Neutral agent: ambiguity penalty dominates → STAY wins.
    High dopamine (low aw): ambiguity ignored → still STAY (lower KL).
    High cortisol (high rw): risk amplified → STAY even more favored.
    """
    num_actions, num_states = 2, 2

    # Observations: 2 obs, 2 states
    # State 0 (Home): very noisy observations
    # State 1 (Away): very clear observations
    L = np.array([
        [0.55, 0.95],  # obs 0
        [0.45, 0.05],  # obs 1
    ])

    # Preferences: strongly favor State 0 (Home/Safe)
    prefs = np.array([0.85, 0.15])

    T = np.zeros((num_actions, num_states, num_states))
    # STAY: keeps you in State 0
    T[0] = np.array([
        [0.9, 0.1],
        [0.3, 0.7],
    ])
    # VENTURE: pushes toward State 1
    T[1] = np.array([
        [0.3, 0.7],
        [0.1, 0.9],
    ])

    belief = np.array([0.7, 0.3])
    return num_actions, num_states, L, prefs, T, belief


def _compute_efe(rw, aw, scenario=None):
    """Compute raw EFE for both actions."""
    na, ns, L, prefs, T, belief = scenario or _build_conflict_scenario()
    efe = np.zeros(na)
    for a in range(na):
        qs = T[a] @ belief
        qs = qs / (qs.sum() + 1e-12)
        kl = np.sum(qs * np.log((qs + 1e-12) / (prefs + 1e-12)))
        amb = 0.0
        for s in range(ns):
            if qs[s] > 1e-12:
                p = L[:, s]
                h = -np.sum(p * np.log(p + 1e-12))
                amb += qs[s] * h
        efe[a] = rw * kl + aw * amb
    return efe


def _tick_n(endo, n: int) -> None:
    """Run homeostasis n times to simulate ticks."""
    for _ in range(n):
        endo._homeostasis()


class TestEFEWeights(unittest.TestCase):
    """Verify pure weight calculations (no scenario dependency)."""

    def test_baseline_weights(self):
        endo = DigitalEndocrine()
        endo.cortisol = 0.0
        endo.dopamine = 0.0
        endo.oxytocin = 0.0
        endo.melatonin = 0.0
        bio = BiologicallyModulatedEngine(
            ActiveInferenceEngine(2, 2), endo,
        )
        rw, aw = bio.get_efe_weights()
        self.assertAlmostEqual(rw, 1.0, places=1)
        self.assertAlmostEqual(aw, 1.0, places=1)

    def test_cortisol_raises_risk_weight(self):
        endo = DigitalEndocrine()
        endo.cortisol = 0.8
        bio = BiologicallyModulatedEngine(
            ActiveInferenceEngine(2, 2), endo,
        )
        rw, _ = bio.get_efe_weights()
        self.assertGreater(rw, 4.0)

    def test_dopamine_lowers_ambiguity_weight(self):
        endo = DigitalEndocrine()
        endo.dopamine = 0.9
        bio = BiologicallyModulatedEngine(
            ActiveInferenceEngine(2, 2), endo,
        )
        _, aw = bio.get_efe_weights()
        self.assertLess(aw, 0.2)

    def test_melatonin_raises_both_weights(self):
        endo = DigitalEndocrine()
        endo.melatonin = 0.8
        endo.oxytocin = 0.0
        endo.dopamine = 0.0  # isolate melatonin effect
        bio = BiologicallyModulatedEngine(
            ActiveInferenceEngine(2, 2), endo,
        )
        rw, aw = bio.get_efe_weights()
        # melatonin adds 0.8*2.0=1.6 to risk, 0.8*0.5=0.4 to ambiguity
        self.assertGreater(rw, 2.5)
        self.assertGreater(aw, 1.3)

    def test_oxytocin_lowers_risk_weight(self):
        endo = DigitalEndocrine()
        endo.cortisol = 0.6
        endo.oxytocin = 0.9
        bio = BiologicallyModulatedEngine(
            ActiveInferenceEngine(2, 2), endo,
        )
        rw, _ = bio.get_efe_weights()
        # Without oxy: 1.0 + 3.0 = 4.0. With oxy: 4.0 - 1.35 = 2.65
        self.assertLess(rw, 3.0)

    def test_composition(self):
        endo = DigitalEndocrine()
        endo.cortisol = 0.5
        endo.dopamine = 0.8
        endo.melatonin = 0.3
        endo.oxytocin = 0.2
        bio = BiologicallyModulatedEngine(
            ActiveInferenceEngine(2, 2), endo,
        )
        rw, aw = bio.get_efe_weights()
        # risk: 1.0 + 2.5 + 0.6 - 0.3 = 3.8
        self.assertAlmostEqual(rw, 3.8, places=1)
        # ambiguity: 1.0 - 0.76 + 0.15 = 0.39
        self.assertAlmostEqual(aw, 0.39, places=1)


class TestBehavioralShifts(unittest.TestCase):
    """Verify relative EFE shifts from hormonal modulation."""

    def test_cortisol_amplifies_efe_gap(self):
        """Higher risk_weight amplifies the KL difference between actions."""
        efe_neutral = _compute_efe(1.0, 1.0)
        efe_stressed = _compute_efe(6.0, 1.0)

        gap_neutral = abs(efe_neutral[1] - efe_neutral[0])
        gap_stressed = abs(efe_stressed[1] - efe_stressed[0])

        # Higher risk_weight should amplify the gap between actions
        self.assertGreater(
            gap_stressed, gap_neutral,
            "Cortisol should amplify behavioral separation",
        )

    def test_dopamine_compresses_efe_gap(self):
        """Lower ambiguity_weight removes ambiguity contribution."""
        efe_neutral = _compute_efe(1.0, 1.0)
        efe_curious = _compute_efe(1.0, 0.05)

        # With low aw, the ambiguity contribution shrinks
        amb_contribution_neutral = efe_neutral.sum()
        amb_contribution_curious = efe_curious.sum()
        self.assertLess(
            amb_contribution_curious, amb_contribution_neutral,
            "Dopamine should reduce total EFE (less ambiguity penalty)",
        )

    def test_homeostatic_action_with_safety_prefs(self):
        """With safety-oriented prefs, STAY should be preferred."""
        efe = _compute_efe(1.0, 1.0)
        self.assertEqual(
            int(np.argmin(efe)), 0,
            "With safety prefs, STAY should be the default action",
        )

    def test_melatonin_increases_conservatism(self):
        """Melatonin raises both weights → STAY becomes even more dominant."""
        efe_awake = _compute_efe(1.0, 1.0)
        # melatonin=0.9: rw += 1.8, aw += 0.45
        efe_sleepy = _compute_efe(2.8, 1.45)

        # STAY advantage should increase when sleepy
        advantage_awake = efe_awake[1] - efe_awake[0]
        advantage_sleepy = efe_sleepy[1] - efe_sleepy[0]
        self.assertGreater(
            advantage_sleepy, advantage_awake,
            "Sleepy agent should have stronger STAY preference",
        )


class TestAgonistsAntagonists(unittest.TestCase):
    """Phase 4: Verify agonist/antagonist pharmacological modulation."""

    def test_agonist_raises_target(self):
        """Injecting a cortisol agonist should raise cortisol."""
        endo = DigitalEndocrine()
        endo.cortisol = 0.0
        sub = Substance("test_agonist", "cortisol", "agonist", potency=0.3, half_life=5.0)
        endo.inject(sub)
        _tick_n(endo, 1)
        # Cortisol should have risen (agonist adds, then decay subtracts 0.02)
        self.assertGreater(endo.cortisol, 0.2)

    def test_antagonist_lowers_target(self):
        """Injecting a dopamine antagonist should suppress dopamine."""
        endo = DigitalEndocrine()
        endo.dopamine = 0.8
        sub = Substance("test_antagonist", "dopamine", "antagonist", potency=0.5, half_life=4.0)
        endo.inject(sub)
        initial = endo.dopamine
        _tick_n(endo, 1)
        # Dopamine should have dropped significantly
        self.assertLess(endo.dopamine, initial - 0.3)

    def test_substance_expires_with_exponential_decay(self):
        """Substances expire when effective_potency < 1%."""
        endo = DigitalEndocrine()
        # potency=0.5, half_life=2: after ~13 ticks potency < 0.01
        sub = Substance("decay_test", "cortisol", "agonist", potency=0.5, half_life=2.0)
        endo.inject(sub)
        self.assertEqual(len(endo.active_substances), 1)
        # After enough ticks the substance should be purged
        _tick_n(endo, 15)
        self.assertEqual(len(endo.active_substances), 0)

    def test_exponential_decay_curve(self):
        """Verify potency follows 0.5^(elapsed/half_life) curve."""
        sub = Substance("curve", "cortisol", "agonist", potency=1.0, half_life=4.0)
        # At t=0: potency = 1.0
        self.assertAlmostEqual(sub.effective_potency, 1.0, places=2)
        # At t=4 (one half-life): potency = 0.5
        sub.elapsed = 4.0
        self.assertAlmostEqual(sub.effective_potency, 0.5, places=2)
        # At t=8 (two half-lives): potency = 0.25
        sub.elapsed = 8.0
        self.assertAlmostEqual(sub.effective_potency, 0.25, places=2)

    def test_compound_caffeine(self):
        """Caffeine should raise cortisol+dopamine and lower melatonin."""
        from cortex.sovereign.pharmacopoeia import caffeine

        endo = DigitalEndocrine()
        endo.cortisol = 0.0
        endo.dopamine = 0.0
        endo.melatonin = 0.5
        subs = caffeine(potency=0.5, half_life=4.0)
        endo.inject_many(subs)
        _tick_n(endo, 1)
        self.assertGreater(endo.cortisol, 0.1, "Caffeine should raise cortisol")
        self.assertGreater(endo.dopamine, 0.1, "Caffeine should raise dopamine")
        self.assertLess(endo.melatonin, 0.3, "Caffeine should lower melatonin")

    def test_clear_by_target(self):
        """clear(target) should remove only substances for that hormone."""
        endo = DigitalEndocrine()
        endo.inject(Substance("a", "cortisol", "agonist", 0.3, 5.0))
        endo.inject(Substance("b", "dopamine", "agonist", 0.3, 5.0))
        removed = endo.clear("cortisol")
        self.assertEqual(removed, 1)
        self.assertEqual(len(endo.active_substances), 1)
        self.assertEqual(endo.active_substances[0].target, "dopamine")

    def test_clear_all(self):
        """clear() with no args should remove ALL substances."""
        endo = DigitalEndocrine()
        endo.inject(Substance("a", "cortisol", "agonist", 0.3, 5.0))
        endo.inject(Substance("b", "dopamine", "agonist", 0.3, 5.0))
        endo.inject(Substance("c", "melatonin", "antagonist", 0.3, 5.0))
        removed = endo.clear()
        self.assertEqual(removed, 3)
        self.assertEqual(len(endo.active_substances), 0)

    def test_efe_shift_under_anxiolytic(self):
        """Anxiolytic should lower risk_weight via cortisol suppression."""
        from cortex.sovereign.pharmacopoeia import anxiolytic

        endo = DigitalEndocrine()
        endo.cortisol = 0.8
        bio = BiologicallyModulatedEngine(
            ActiveInferenceEngine(2, 2), endo,
        )
        rw_before, _ = bio.get_efe_weights()

        # Inject anxiolytic and tick a few times
        bio.inject_many(anxiolytic(potency=0.5, half_life=5.0))
        _tick_n(endo, 3)

        rw_after, _ = bio.get_efe_weights()
        self.assertLess(
            rw_after, rw_before,
            "Anxiolytic should reduce risk_weight by suppressing cortisol",
        )


class TestReceptorCompetition(unittest.TestCase):
    """Phase 4.1: Verify receptor competition model."""

    def test_antagonist_blocks_agonist_same_target(self):
        """Equal agonist + antagonist on same target = net zero effect."""
        endo = DigitalEndocrine()
        endo.cortisol = 0.3
        # Inject matched agonist and antagonist
        endo.inject(Substance("boost", "cortisol", "agonist", 0.4, 5.0))
        endo.inject(Substance("block", "cortisol", "antagonist", 0.4, 5.0))
        initial = endo.cortisol
        _tick_n(endo, 1)
        # Net substance effect should be ~0, only natural decay should apply
        # Cortisol should decrease by roughly the decay amount (0.02)
        self.assertAlmostEqual(endo.cortisol, initial - 0.02, places=1)

    def test_stronger_agonist_wins(self):
        """Stronger agonist overpowers weaker antagonist."""
        endo = DigitalEndocrine()
        endo.cortisol = 0.2
        endo.inject(Substance("strong_boost", "cortisol", "agonist", 0.6, 5.0))
        endo.inject(Substance("weak_block", "cortisol", "antagonist", 0.2, 5.0))
        _tick_n(endo, 1)
        # Net effect = 0.6 - 0.2 = +0.4, minus decay
        self.assertGreater(endo.cortisol, 0.5)

    def test_stronger_antagonist_wins(self):
        """Stronger antagonist overpowers weaker agonist."""
        endo = DigitalEndocrine()
        endo.dopamine = 0.7
        endo.inject(Substance("weak_boost", "dopamine", "agonist", 0.1, 5.0))
        endo.inject(Substance("strong_block", "dopamine", "antagonist", 0.5, 5.0))
        _tick_n(endo, 1)
        # Net effect = 0.1 - 0.5 = -0.4, minus decay
        self.assertLess(endo.dopamine, 0.4)


class TestTolerance(unittest.TestCase):
    """Phase 4.1: Verify tolerance (repeated exposure reduces potency)."""

    def test_first_injection_full_potency(self):
        """First injection should have full potency."""
        endo = DigitalEndocrine()
        endo.cortisol = 0.0
        sub = Substance("test_tol", "cortisol", "agonist", potency=0.5, half_life=5.0)
        endo.inject(sub)
        # Potency should remain 0.5 (no prior exposure)
        self.assertAlmostEqual(sub.potency, 0.5, places=2)

    def test_repeated_injection_reduces_potency(self):
        """Each re-injection should reduce potency by 10%."""
        endo = DigitalEndocrine()
        endo.cortisol = 0.0

        # First injection
        s1 = Substance("tol_drug", "cortisol", "agonist", potency=0.5, half_life=3.0)
        endo.inject(s1)
        p1 = s1.potency
        _tick_n(endo, 4)  # let it expire

        # Second injection — should have 90% of original
        s2 = Substance("tol_drug", "cortisol", "agonist", potency=0.5, half_life=3.0)
        endo.inject(s2)
        p2 = s2.potency
        self.assertAlmostEqual(p2 / 0.5, 0.9, places=2)
        self.assertLess(p2, p1)

    def test_tolerance_reset(self):
        """reset_tolerance should restore full potency."""
        endo = DigitalEndocrine()
        # Build up tolerance
        for _ in range(5):
            s = Substance("reset_drug", "cortisol", "agonist", potency=0.5, half_life=2.0)
            endo.inject(s)
            _tick_n(endo, 3)

        self.assertGreater(endo._tolerance["reset_drug"], 0)
        endo.reset_tolerance("reset_drug")

        # Next injection should be full potency
        s_fresh = Substance("reset_drug", "cortisol", "agonist", potency=0.5, half_life=5.0)
        endo.inject(s_fresh)
        self.assertAlmostEqual(s_fresh.potency, 0.5, places=2)


class TestSubstanceCap(unittest.TestCase):
    """Phase 4.1: Verify substance cap and safety limits."""

    def test_cap_rejects_overflow(self):
        """Cannot inject more than MAX_ACTIVE_SUBSTANCES."""
        endo = DigitalEndocrine()
        for i in range(MAX_ACTIVE_SUBSTANCES):
            endo.inject(Substance(f"sub_{i}", "cortisol", "agonist", 0.01, 100.0))
        with self.assertRaises(RuntimeError):
            endo.inject(Substance("overflow", "cortisol", "agonist", 0.01, 100.0))

    def test_cap_allows_after_clear(self):
        """After clearing, new injections should succeed."""
        endo = DigitalEndocrine()
        for i in range(MAX_ACTIVE_SUBSTANCES):
            endo.inject(Substance(f"sub_{i}", "cortisol", "agonist", 0.01, 100.0))
        endo.clear()
        # Should succeed now
        endo.inject(Substance("fresh", "cortisol", "agonist", 0.3, 5.0))
        self.assertEqual(len(endo.active_substances), 1)


class TestSubstanceRepr(unittest.TestCase):
    """Phase 4.1: Verify __repr__ and to_dict."""

    def test_repr_format(self):
        sub = Substance("caffeine:cortisol", "cortisol", "agonist", 0.3, 5.0)
        r = repr(sub)
        self.assertIn("caffeine:cortisol", r)
        self.assertIn("agonist", r)
        self.assertIn("cortisol", r)

    def test_to_dict_includes_substances(self):
        endo = DigitalEndocrine()
        endo.inject(Substance("test_sub", "dopamine", "agonist", 0.3, 5.0))
        d = endo.to_dict()
        self.assertIn("active_substances", d)
        self.assertEqual(len(d["active_substances"]), 1)
        self.assertEqual(d["active_substances"][0]["name"], "test_sub")

    def test_to_dict_includes_tolerance(self):
        endo = DigitalEndocrine()
        endo.inject(Substance("tol_test", "cortisol", "agonist", 0.3, 5.0))
        d = endo.to_dict()
        self.assertIn("tolerance", d)
        self.assertIn("tol_test", d["tolerance"])


if __name__ == "__main__":
    unittest.main()
