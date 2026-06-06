# [C5-REAL] Exergy-Maximized
"""
Test: CORTEX Inverse Engine - Python Integration (C5-REAL)

Validates the full Rust→Python bridge for the inverse AlphaProof pipeline.
Requires: maturin develop (or pre-built cortex_rs.so)
"""

import json
import time
import pytest


def _try_import():
    """Attempt to import cortex_rs with the inverse engine classes."""
    try:
        import cortex_rs

        # Check that the new classes exist
        assert hasattr(cortex_rs, "DeductionDAG"), "DeductionDAG not exported"
        assert hasattr(cortex_rs, "CurriculumEngine"), "CurriculumEngine not exported"
        assert hasattr(cortex_rs, "EvolutionaryConjecturer"), "EvolutionaryConjecturer not exported"
        assert hasattr(cortex_rs, "InverseEngine"), "InverseEngine not exported"
        return cortex_rs
    except (ImportError, AssertionError):
        return None


# Skip all tests if cortex_rs is not built
cortex_rs = _try_import()
skip_reason = "cortex_rs not built (run: cd cortex_rs && maturin develop --release)"
requires_cortex = pytest.mark.skipif(cortex_rs is None, reason=skip_reason)


# ─────────────────────────────────────────────────────────────
# §1 - DeductionDAG Tests
# ─────────────────────────────────────────────────────────────


@requires_cortex
class TestDeductionDAG:
    def test_axiom_creation(self):
        dag = cortex_rs.DeductionDAG()
        id0 = dag.add_axiom("point(A)")
        id1 = dag.add_axiom("point(B)")
        assert id0 == 0
        assert id1 == 1
        assert dag.axiom_count() == 2
        assert dag.fact_count() == 2

    def test_derivation(self):
        dag = cortex_rs.DeductionDAG()
        a = dag.add_axiom("point(A)")
        b = dag.add_axiom("point(B)")
        d = dag.derive("line(A,B)", [a, b], "two_points_line")
        assert d is not None
        assert dag.fact_count() == 3
        assert dag.derived_count() == 1
        assert dag.max_depth() == 1

    def test_traceback(self):
        dag = cortex_rs.DeductionDAG()
        a = dag.add_axiom("point(A)")
        b = dag.add_axiom("point(B)")
        aux = dag.add_auxiliary("midpoint(M,A,B)")
        d1 = dag.derive("segment(A,M)", [a, aux], "midpoint_segment")
        d2 = dag.derive("equal(AM,MB)", [d1, aux, b], "midpoint_equal")

        result = json.loads(dag.traceback(d2))
        assert result["conclusion"] == d2
        assert len(result["minimal_premises"]) >= 1
        assert len(result["auxiliary_constructions"]) >= 1
        assert result["proof_depth"] >= 2

    def test_synthetic_triples(self):
        dag = cortex_rs.DeductionDAG()
        a = dag.add_axiom("p1")
        b = dag.add_axiom("p2")
        aux = dag.add_auxiliary("aux1")
        d1 = dag.derive("d1", [a, aux], "r1")
        d2 = dag.derive("d2", [d1, b], "r2")

        triples = json.loads(dag.generate_synthetic_triples())
        assert isinstance(triples, list)

    def test_get_fact(self):
        dag = cortex_rs.DeductionDAG()
        fid = dag.add_axiom("test_fact")
        fact = json.loads(dag.get_fact(fid))
        assert fact["content"] == "test_fact"
        assert fact["depth"] == 0


# ─────────────────────────────────────────────────────────────
# §2 - CurriculumEngine Tests
# ─────────────────────────────────────────────────────────────


@requires_cortex
class TestCurriculumEngine:
    def test_target_and_generate(self):
        eng = cortex_rs.CurriculumEngine()
        tid = eng.set_target(["p1", "p2", "p3"], "goal", 0.9)
        assert len(tid) == 64  # hex-encoded SHA-256

        eng.add_substitution("p1", "simple_p1")
        generated = eng.generate(2)
        assert generated > 0
        assert eng.len() > 1

    def test_stats(self):
        eng = cortex_rs.CurriculumEngine()
        eng.set_target(["a", "b", "c"], "g", 0.8)
        eng.add_substitution("a", "x")
        eng.generate(2)
        stats = json.loads(eng.stats())
        assert stats["total_variants"] > 1
        assert stats["min_difficulty"] < 0.8

    def test_solve_rate(self):
        eng = cortex_rs.CurriculumEngine()
        eng.set_target(["p1"], "g", 0.5)
        assert eng.solve_rate() == 0.0
        assert not eng.is_target_solved()


# ─────────────────────────────────────────────────────────────
# §3 - EvolutionaryConjecturer Tests
# ─────────────────────────────────────────────────────────────


@requires_cortex
class TestConjecturer:
    def test_seed_and_evolve(self):
        c = cortex_rs.EvolutionaryConjecturer(max_population=50)
        hex_id = c.seed(["hyp1", "hyp2"], "conclusion", 700.0)
        assert len(hex_id) == 64

        c.add_negate_mutation()
        c.add_premise_mutation("extra_hyp")

        stats = json.loads(c.evolve())
        assert stats["generation"] == 1
        assert stats["population_size"] >= 1

    def test_verification_lifecycle(self):
        c = cortex_rs.EvolutionaryConjecturer(max_population=50)
        id1 = c.seed(["a"], "b", 500.0)
        id2 = c.seed(["c"], "d", 500.0)

        c.mark_proven(id1)
        c.mark_refuted(id2, "counterexample x=0")

        assert c.proven_count() == 1
        assert c.surviving_count() == 0  # both resolved

    def test_top_conjectures(self):
        c = cortex_rs.EvolutionaryConjecturer(max_population=50)
        for i in range(5):
            c.seed([f"h{i}"], f"c{i}", 100.0 * (i + 1))

        top = json.loads(c.top_conjectures(3))
        assert len(top) == 3


# ─────────────────────────────────────────────────────────────
# §4 - InverseEngine (Full Pipeline) Tests
# ─────────────────────────────────────────────────────────────


@requires_cortex
class TestInverseEngine:
    def test_full_pipeline(self):
        eng = cortex_rs.InverseEngine(
            conjecturer_population=50,
            evolution_cycles=2,
            curriculum_depth=2,
            traceback_max_depth=5,
            difficulty_threshold=0.3,
            batch_size=10,
        )

        # Seed conjectures
        for i in range(3):
            eng.seed([f"hyp_{i}_a", f"hyp_{i}_b"], f"thm_{i}", 600.0)

        eng.add_negate_mutation()
        eng.add_premise_mutation("axiom_x")

        # Run iteration with threshold solver
        telemetry = json.loads(eng.iterate_threshold(max_premises=5))
        assert telemetry["iteration"] == 1
        assert telemetry["problems_attempted"] > 0
        assert telemetry["conjectures_generated"] > 0

    def test_multiple_iterations(self):
        eng = cortex_rs.InverseEngine(
            conjecturer_population=30,
            evolution_cycles=1,
            curriculum_depth=2,
        )
        for i in range(3):
            eng.seed([f"p{i}"], f"g{i}", 500.0)
        eng.add_negate_mutation()

        for _ in range(3):
            eng.iterate_threshold(max_premises=3)

        assert eng.current_iteration() == 3
        assert eng.population_size() > 3

        stats = json.loads(eng.cumulative_stats())
        assert stats["iterations"] == 3

    def test_difficulty_solver(self):
        eng = cortex_rs.InverseEngine(
            conjecturer_population=20,
            evolution_cycles=1,
            curriculum_depth=2,
            batch_size=5,
        )
        eng.seed(["short"], "g", 500.0)
        eng.add_negate_mutation()

        telemetry = json.loads(eng.iterate_difficulty(threshold=1.0))
        assert telemetry["iteration"] == 1

    def test_training_data_accumulation(self):
        eng = cortex_rs.InverseEngine(
            conjecturer_population=30,
            evolution_cycles=1,
            curriculum_depth=2,
        )
        eng.seed(["a", "b"], "c", 500.0)
        eng.add_premise_mutation("d")

        eng.iterate_threshold(max_premises=5)
        count_1 = eng.training_data_count()

        eng.iterate_threshold(max_premises=5)
        count_2 = eng.training_data_count()

        assert count_2 >= count_1

    def test_telemetry_history(self):
        eng = cortex_rs.InverseEngine()
        eng.seed(["x"], "y", 500.0)
        eng.add_negate_mutation()

        eng.iterate_threshold(max_premises=3)
        eng.iterate_threshold(max_premises=3)

        history = json.loads(eng.telemetry())
        assert len(history) == 2
        assert history[0]["iteration"] == 1
        assert history[1]["iteration"] == 2


# ─────────────────────────────────────────────────────────────
# §5 - Benchmark
# ─────────────────────────────────────────────────────────────


@requires_cortex
@pytest.mark.slow
class TestBenchmark:
    def test_pipeline_throughput(self):
        eng = cortex_rs.InverseEngine(
            conjecturer_population=50,
            evolution_cycles=2,
            curriculum_depth=2,
            batch_size=10,
        )

        for i in range(10):
            eng.seed(
                [f"h_{i}_{j}" for j in range(4)],
                f"thm_{i}",
                500.0 + i * 50.0,
            )
        eng.add_negate_mutation()
        eng.add_premise_mutation("extra")
        eng.add_swap_mutation("0", "1")

        # Measure baseline empty loop overhead to calibrate load
        iterations = 1000
        start_base = time.perf_counter()
        for _ in range(iterations):
            pass
        elapsed_base = time.perf_counter() - start_base
        base_us = (elapsed_base / iterations) * 1000000

        t0 = time.perf_counter()
        for _ in range(3):
            eng.iterate_threshold(max_premises=4)
        elapsed = time.perf_counter() - t0

        stats = json.loads(eng.cumulative_stats())
        rate = stats["total_solved"] / elapsed if elapsed > 0 else 0

        # Just verify it runs - exact rate depends on hardware
        assert stats["iterations"] == 3
        # Adjust limit based on baseline CPU latency
        limit = max(15.0, 15.0 + (base_us - 1.0) * 5.0)
        assert elapsed < limit, (
            f"Pipeline should complete 3 iterations in < {limit:.2f}s (elapsed: {elapsed:.2f}s, base_us: {base_us:.4f})"
        )
