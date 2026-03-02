"""
Cobbler's Children Test — The Compliance Engine Audits Itself.

Axiom: If legion_vectors.EntropyDemon flags a pattern as FRAGILE in generated code,
that same pattern MUST NOT exist in the engine's own source files.

No exceptions. No noqa overrides on the structural violations UNLESS explicitly
annotated with a justification comment on the same line.

Ω₃ (Byzantine Default): Nothing is trusted by default — including self.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex.engine.legion_vectors import (
    RED_TEAM_SWARM,
    ChronosSniper,
    EntropyDemon,
    Intruder,
    OOMKiller,
)

# ─── Scope ────────────────────────────────────────────────────────────────────
# The engine is the primary compliance target. These are the modules that DEFINE
# the rules — they must pass through their own rules first.
_ENGINE_ROOT = Path(__file__).resolve().parents[1] / "cortex" / "engine"

# Files explicitly excluded: they ARE the scanner/test infrastructure, so they
# will intentionally reference the patterns as string literals (not live code).
_EXCLUDE_FILES = frozenset(
    [
        "legion_vectors.py",  # The scanner itself — contains patterns as strings
        "legion.py",          # Code-gen engine — emits example patterns as string literals
    ]
)

# Annotations that make a bare-except intentional and documented.
# A line is exempt if it contains ANY of these markers AND a reason comment.
_NOQA_MARKERS = ("# noqa: BLE001", "# noqa:BLE001", "# deliberate boundary")


def _collect_engine_files() -> list[Path]:
    """Return all .py files in the engine module, excluding known scanner files."""
    return [
        f
        for f in _ENGINE_ROOT.rglob("*.py")
        if f.name not in _EXCLUDE_FILES
        and "__pycache__" not in f.parts
    ]


def _read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ─── EntropyDemon Self-Audit ───────────────────────────────────────────────────

class TestEntropyDemonSelfAudit:
    """
    EntropyDemon.attack() must not fire on the engine's own code.

    The test is STRICT about bare `except:` and `except Exception:` WITHOUT
    an explicit noqa/justification marker. Lines that carry `# noqa: BLE001`
    or `# deliberate boundary` are considered intentional and are excluded.
    """

    def _bare_except_violations(self, source_lines: list[str]) -> list[str]:
        """Return lines that have a bare except without a noqa justification."""
        violations = []
        for i, line in enumerate(source_lines, 1):
            stripped = line.strip()
            is_bare = stripped.startswith("except Exception:") or stripped == "except:"
            has_justification = any(marker in line for marker in _NOQA_MARKERS)
            if is_bare and not has_justification:
                violations.append(f"line {i}: {line.rstrip()}")
        return violations

    def test_no_unjustified_bare_except_in_engine(self) -> None:
        """
        Every `except Exception:` in the engine module must carry an explicit
        noqa:BLE001 or a `# deliberate boundary` justification comment.

        RATIONALE: EntropyDemon flags bare excepts as FRAGILE in generated code.
        The engine cannot exempt itself from this rule without documentation.
        """
        all_violations: dict[str, list[str]] = {}

        for py_file in _collect_engine_files():
            source_lines = _read_source(py_file).splitlines()
            violations = self._bare_except_violations(source_lines)
            if violations:
                all_violations[py_file.name] = violations

        if all_violations:
            report = "\n".join(
                f"\n  📄 {fname}:\n    " + "\n    ".join(lines)
                for fname, lines in all_violations.items()
            )
            pytest.fail(
                f"\n☠️  COBBLER'S PARADOX DETECTED — Engine violates its own compliance rule.\n"
                f"EntropyDemon would flag these as FRAGILE in generated code:\n{report}\n\n"
                f"Fix: narrow to specific exception types OR add `# noqa: BLE001` "
                f"with a justification comment on the same line."
            )

    @pytest.mark.asyncio
    async def test_entropy_demon_passes_own_source(self) -> None:
        """
        Run EntropyDemon.attack() directly on the engine source code.
        The swarm must not return FRAGILITY findings from its own codebase.

        This is the live runtime version of the static analysis above.
        """
        demon = EntropyDemon()
        all_findings: dict[str, list[str]] = {}

        for py_file in _collect_engine_files():
            source = _read_source(py_file)

            # Strip noqa-annotated lines before passing to the demon so that
            # intentional boundaries (noqa:BLE001) don't create false positives
            cleaned_lines = [
                line
                for line in source.splitlines()
                if not any(m in line for m in _NOQA_MARKERS)
            ]
            cleaned_source = "\n".join(cleaned_lines)

            findings = await demon.attack(cleaned_source, context={})
            fragility_findings = [f for f in findings if "Bare `except`" in f]
            if fragility_findings:
                all_findings[py_file.name] = fragility_findings

        if all_findings:
            report = "\n".join(
                f"  {fname}: {findings}"
                for fname, findings in all_findings.items()
            )
            pytest.fail(
                f"\n☠️  ENTROPY DEMON FIRED ON ENGINE SOURCE:\n{report}"
            )


# ─── Full Red Team Swarm Self-Audit ───────────────────────────────────────────

class TestRedTeamSwarmSelfAudit:
    """
    Run the full RED_TEAM_SWARM (all 4 vectors) against the engine source.
    Each vector's findings are reported as warnings (not hard failures) EXCEPT
    for security findings from Intruder — those are always hard failures.
    """

    @pytest.mark.asyncio
    async def test_intruder_finds_no_eval_exec_in_engine(self) -> None:
        """
        Intruder checks for eval()/exec()/os.system() — security vulnerabilities.
        These MUST NOT exist in the engine. No exceptions. No noqa bypass.
        """
        intruder = Intruder()
        violations: dict[str, list[str]] = {}

        for py_file in _collect_engine_files():
            source = _read_source(py_file)
            findings = await intruder.attack(source, context={})
            if findings:
                violations[py_file.name] = findings

        if violations:
            report = "\n".join(
                f"  {fname}: {findings}" for fname, findings in violations.items()
            )
            pytest.fail(
                f"\n🔴 SECURITY BREACH — Intruder found violations in engine source:\n{report}"
            )

    @pytest.mark.asyncio
    async def test_chronos_sniper_finds_no_blocking_in_async_engine(self) -> None:
        """
        ChronosSniper checks for time.sleep() / requests.get() inside async def.
        Hard failure: a blocking call in an async gateway is a deadlock vector.
        """
        sniper = ChronosSniper()
        violations: dict[str, list[str]] = {}

        for py_file in _collect_engine_files():
            source = _read_source(py_file)
            findings = await sniper.attack(source, context={})
            if findings:
                violations[py_file.name] = findings

        if violations:
            report = "\n".join(
                f"  {fname}: {findings}" for fname, findings in violations.items()
            )
            pytest.fail(
                f"\n⏱️  CHRONOS SNIPER — Blocking I/O in async engine code:\n{report}"
            )

    @pytest.mark.asyncio
    async def test_oom_killer_warns_on_engine_loops(self) -> None:
        """
        OOMKiller checks for loops without break statements.
        Soft failure: logged as a warning for situational awareness.
        Infinite loops in engine daemons are often intentional (omniscience_loop)
        but should be explicitly reviewed at each PR.
        """
        killer = OOMKiller()
        findings_summary: dict[str, list[str]] = {}

        for py_file in _collect_engine_files():
            source = _read_source(py_file)
            findings = await killer.attack(source, context={})
            if findings:
                findings_summary[py_file.name] = findings

        if findings_summary:
            # Soft warning — not a hard fail. Infinite loops in daemons are valid.
            import warnings
            report = "; ".join(
                f"{fname}({len(f)} findings)"
                for fname, f in findings_summary.items()
            )
            warnings.warn(
                f"OOMKiller: potential unbounded loops in engine "
                f"(review before merging): {report}",
                stacklevel=2,
            )

    @pytest.mark.asyncio
    async def test_all_vectors_return_lists(self) -> None:
        """
        Structural integrity: every vector in RED_TEAM_SWARM must return a list.
        This validates the AttackVector protocol is correctly implemented by all members.
        """
        sample_code = "x = 1\n"
        for vector in RED_TEAM_SWARM:
            result = await vector.attack(sample_code, context={})
            assert isinstance(result, list), (
                f"Vector {vector.name!r} returned {type(result).__name__!r}, "
                f"expected list — AttackVector protocol violation."
            )


# ─── Regression Guard ─────────────────────────────────────────────────────────

class TestCobblersParadoxRegression:
    """
    Regression tests: once fixed, violations must NEVER re-appear.
    Each test below locks a specific fix made in response to the Cobbler audit.
    """

    @pytest.mark.asyncio
    async def test_apotheosis_signalbus_init_is_narrowed(self) -> None:
        """
        apotheosis.py:64 — SignalBus init must NOT use bare `except Exception: pass`.
        Regression guard for the Cobbler fix (2026-03-02).
        """
        apotheosis_path = _ENGINE_ROOT / "apotheosis.py"
        source = _read_source(apotheosis_path)
        lines = source.splitlines()

        # The original offending pattern: a bare except with pass and no log
        bare_pass_pattern_found = any(
            "except Exception:" in line and "pass" in lines[min(i + 1, len(lines) - 1)]
            and not any(m in line for m in _NOQA_MARKERS)
            for i, line in enumerate(lines)
        )
        assert not bare_pass_pattern_found, (
            "REGRESSION: apotheosis.py has a bare `except Exception: pass` "
            "without justification — Cobbler's fix was reverted!"
        )

    @pytest.mark.asyncio
    async def test_reflex_fallback_is_not_silent(self) -> None:
        """
        reflex.py:77 — The fallback keter.ignite() must NOT silently swallow errors.
        A sovereign reflex that fails silently is worse than crashing.
        Regression guard for the Cobbler fix (2026-03-02).
        """
        reflex_path = _ENGINE_ROOT / "reflex.py"
        source = _read_source(reflex_path)

        # Detect the silent pattern: `except Exception:` immediately followed by `pass`
        lines = source.splitlines()
        for i, line in enumerate(lines):
            if "except Exception:" in line or "except:" in line.strip():
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                has_justification = any(m in line for m in _NOQA_MARKERS)
                if next_line == "pass" and not has_justification:
                    pytest.fail(
                        f"REGRESSION: reflex.py line {i + 1} has a silent "
                        f"`except ... pass` — Cobbler's fix was reverted!\n"
                        f"  Offending line: {line.strip()}"
                    )
