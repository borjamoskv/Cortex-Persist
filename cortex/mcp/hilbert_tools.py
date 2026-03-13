"""MCP tool registration for Hilbert-Omega theorem prover."""

from __future__ import annotations

import logging

logger = logging.getLogger("cortex.mcp.hilbert")


def register_hilbert_tools(mcp, ctx) -> None:  # type: ignore
    """Register ``cortex_hilbert_omega`` tool on the MCP server."""

    @mcp.tool()
    async def cortex_hilbert_omega(
        attack: str = "conjectures",
        problem: str = "",
    ) -> str:
        """Run a formal verification or brute-force attack on a mathematical conjecture.

        Attack modes:
          - "conjectures": Run Collatz, Goldbach, Twin Primes, ABC
          - "millennium": Run the 6 Clay Millennium Problem vectors
          - "prove": Use Z3 to prove a named theorem ("euclides")

        Args:
            attack: Attack mode ("conjectures", "millennium", "prove").
            problem: For "prove" mode, the theorem name.
        """
        import os
        import sys

        # Add scripts dir to path
        skills_dir = os.path.join(
            os.path.expanduser("~"),
            ".gemini", "antigravity", "skills",
            "hilbert-omega", "scripts",
        )
        if skills_dir not in sys.path:
            sys.path.insert(0, skills_dir)

        try:
            if attack == "conjectures":
                from conjectures import run_all_conjectures
                results = run_all_conjectures()
                lines = ["Hilbert-Ω Conjectures Report:\n"]
                for r in results:
                    icon = "🟢" if r.counterexample is None else "🔴"
                    lines.append(
                        f"  {icon} {r.name}: {r.detail} "
                        f"[{r.elapsed_ms:.0f}ms]"
                    )

                # Persist summary to CORTEX
                await ctx.ensure_ready()
                from cortex.engine import CortexEngine
                async with ctx.pool.acquire() as conn:
                    engine = CortexEngine(ctx.cfg.db_path, auto_embed=False)
                    engine._conn = conn
                    summary = "; ".join(
                        f"{r.name}: {'OK' if not r.counterexample else 'FAIL'}"
                        for r in results
                    )
                    await engine.store(
                        "HILBERT-OMEGA", summary,
                        "knowledge", ["math", "conjectures"],
                        "C4", "agent:hilbert-omega",
                    )
                return "\n".join(lines)

            elif attack == "millennium":
                from millennium_assault import MillenniumAssaultEngine
                eng = MillenniumAssaultEngine()
                await eng.run_global_assault()
                lines = ["Millennium Assault Report:\n"]
                for r in eng.results:
                    icon = {"discovery": "🟢", "ghost": "🔴", "decision": "🟡", "error": "🟠"}
                    lines.append(
                        f"  {icon.get(r.verdict, '⚪')} [{r.problem}] "
                        f"{r.verdict.upper()} ({r.confidence}) "
                        f"[{r.elapsed_ms:.0f}ms] — {r.detail[:80]}"
                    )
                return "\n".join(lines)

            elif attack == "prove":
                if not problem:
                    return "❌ Specify a theorem name with 'problem' arg."
                from hilbert_engine import attack_theorem
                try:
                    from z3 import Ints
                    x, y = Ints('x y')
                    if problem == "euclides":
                        hypothesis = (x + y == y + x)
                        result = attack_theorem(
                            "Propiedad Conmutativa de la Adición Entera",
                            hypothesis,
                        )
                        return (
                            f"{'✅ DEMOSTRADO' if result else '❌ REFUTADO'}: "
                            f"{problem}"
                        )
                    return f"❌ Theorem '{problem}' not in attack registry."
                except ImportError:
                    return "❌ Z3 not installed."

            return f"❌ Unknown attack mode: {attack}"

        except Exception as e:  # noqa: BLE001
            logger.error("Hilbert-Omega error: %s", e)
            return f"❌ Hilbert-Omega error: {e}"
