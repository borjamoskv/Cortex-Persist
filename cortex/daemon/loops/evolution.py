# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

import asyncio
import itertools
import logging
import time
from pathlib import Path

logger = logging.getLogger("cortex.daemon.loops.evolution")

_MAX_RESONANCES = 100


async def evolution_loop(state, cortex_root, speak_func):
    """Monitors code entropy and suggests refactors."""
    try:
        from analyze_entropy import calculate_module_overlap
    except ImportError:
        # Fallback if analyze_entropy is not on path
        return

    while True:
        try:
            project = state.daemons.get("gidatu", {}).get("current_context")
            if project and project != "None":
                proj_path = cortex_root / project
                if proj_path.exists():
                    files = [str(p) for p in proj_path.glob("*.py")]
                    if len(files) >= 2:
                        for f1, f2 in itertools.combinations(files, 2):
                            overlap = calculate_module_overlap(f1, f2)
                            if overlap > 0.4:
                                ghost_id = f"REF-{int(time.time()) % 1000}"
                                state.daemons["ghost_field"]["resonances"].append(
                                    {
                                        "id": ghost_id,
                                        "project": project,
                                        "intent": (
                                            f"Refactor tight coupling"
                                            f" ({int(overlap * 100)}%)"
                                            f" between {Path(f1).name}"
                                            f" and {Path(f2).name}"
                                        ),
                                        "source": "evolution_loop",
                                        "strength": 0.8,
                                    }
                                )
                                # Cap resonances to prevent OOM
                                res = state.daemons["ghost_field"]["resonances"]
                                if len(res) > _MAX_RESONANCES:
                                    state.daemons["ghost_field"]["resonances"] = res[
                                        -_MAX_RESONANCES:
                                    ]
                                state.daemons["ghost_field"]["active_ghosts"] = len(
                                    state.daemons["ghost_field"]["resonances"]
                                )
                                if not state.daemons.get("mute", False):
                                    await speak_func(
                                        state,
                                        f"Entropía detectada en proyecto"
                                        f" {project}. Sugerencia refactor"
                                        f" {ghost_id} generada.",
                                        voice="Jorge",
                                        rate=150,
                                    )

            await asyncio.sleep(600)
        except Exception as e:
            logger.error("Evolution Loop Error: %s", e)
            await asyncio.sleep(60)
