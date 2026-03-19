"""MCP tool registration for Hilbert-Omega theorem prover."""

from __future__ import annotations

import importlib.util
import logging
import os
from typing import Any

from cortex.mcp.decorators import with_db

logger = logging.getLogger("cortex.mcp.hilbert")

# Skills directory for Hilbert-Omega scripts
_SKILLS_DIR = os.path.join(
    os.path.expanduser("~"),
    ".gemini", "antigravity", "skills", "hilbert-omega", "scripts",
)


def _load_skill_module(name: str):
    """Load a module from the hilbert-omega skills dir without sys.path."""
    path = os.path.join(_SKILLS_DIR, f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def register_hilbert_tools(mcp, ctx) -> None:  # type: ignore
    """Register ``cortex_hilbert_omega`` tool on the MCP server."""

    @mcp.tool()
    @with_db(ctx)
    async def cortex_hilbert_omega(
        conn: Any,
        attack: str = "conjectures",
        problem: str = "",
    ) -> str:
        """Run a formal verification or brute-force attack on a conjecture.

        Attack modes:
          - "conjectures": Run Collatz, Goldbach, Twin Primes, ABC
          - "millennium": Run the 6 Clay Millennium Problem vectors
          - "prove": Use Z3 to prove a named theorem ("euclides")

        Args:
            attack: Attack mode ("conjectures", "millennium", "prove").
            problem: For "prove" mode, the theorem name.
        """
        try:
            if attack == "conjectures":
                mod = _load_skill_module("conjectures")
                results = mod.run_all_conjectures()
                lines = ["Hilbert-Ω Conjectures Report:\n"]
                for r in results:
                    icon = "🟢" if r.counterexample is None else "🔴"
                    lines.append(
                        f"  {icon} {r.name}: {r.detail}"
                        f" [{r.elapsed_ms:.0f}ms]"
                    )

                engine = ctx.engine_from_conn(conn)
                summary = "; ".join(
                    f"{r.name}: {'OK' if not r.counterexample else 'FAIL'}"
                    for r in results
                )
                await engine.store(
                    "HILBERT-OMEGA",
                    summary,
                    "knowledge",
                    ["math", "conjectures"],
                    "C4",
                    "agent:hilbert-omega",
                )
                return "\n".join(lines)

            elif attack == "millennium":
                mod = _load_skill_module("millennium_assault")
                eng = mod.MillenniumAssaultEngine()
                await eng.run_global_assault()
                lines = ["Millennium Assault Report:\n"]
                for r in eng.results:
                    icon = {
                        "discovery": "🟢",
                        "ghost": "🔴",
                        "decision": "🟡",
                        "error": "🟠",
                    }
                    lines.append(
                        f"  {icon.get(r.verdict, '⚪')} [{r.problem}] "
                        f"{r.verdict.upper()} ({r.confidence}) "
                        f"[{r.elapsed_ms:.0f}ms] — {r.detail[:80]}"
                    )
                return "\n".join(lines)

            elif attack == "prove":
                if not problem:
                    return "❌ Specify a theorem name with 'problem' arg."
                mod = _load_skill_module("hilbert_engine")

                try:
                    from z3 import Ints

                    x, y = Ints("x y")
                    if problem == "euclides":
                        hypothesis = x + y == y + x
                        result = mod.attack_theorem(
                            "Propiedad Conmutativa de la Adición Entera",
                            hypothesis,
                        )
                        status = "✅ DEMOSTRADO" if result else "❌ REFUTADO"
                        return f"{status}: {problem}"
                    return f"❌ Theorem '{problem}' not in attack registry."
                except ImportError:
                    return "❌ Z3 not installed."

            return f"❌ Unknown attack mode: {attack}"

        except Exception as e:  # noqa: BLE001
            logger.error("Hilbert-Omega error: %s", e)
            return f"❌ Hilbert-Omega error: {e}"

