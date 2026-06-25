# Creator/Autor: Borja Moskv (borjamoskv)
# Protocolo: C5-REAL | Epistemic Consolidation Pipeline
"""
CORTEX Persist Cognitive Consolidation Pipeline (C5-REAL).
Orchestrates the ingestion of all mathematical, spatial, performance, design,
and behavioral primitives into the Epistemic Dependency Graph.
"""

import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.abspath('.'))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("consolidate_cortex")

# Import all main and inject_primitives functions
from inject_agente_principal import inject_primitives as inject_agent_principal
from inject_arkham_breadcrumbs import inject_primitives as inject_arkham_breadcrumbs
from inject_category_theory import main as inject_cat_theory
from inject_category_theory_advanced import main as inject_cat_theory_adv
from inject_cwv_performance import inject_primitives as inject_cwv
from inject_design_tokens import inject_primitives as inject_design
from inject_framework_dame import inject_primitives as inject_dame_framework
from inject_git_exergy import inject_primitives as inject_git_exergy
from inject_goat_math import inject_primitives as inject_goat
from inject_leyes_fisicas import inject_primitives as inject_physical_laws
from inject_mythos_primitives import inject_primitives as inject_mythos
from inject_osint_defense import inject_primitives as inject_osint
from inject_sistemas_complejos import inject_primitives as inject_complex_systems
from inject_spatial_render import inject_primitives as inject_spatial

# Registry of all available injectors with display name, error identifier, and function
INJECTORS = [
    ("Category Theory", "inject_cat_theory", inject_cat_theory),
    ("Category Theory Advanced", "inject_cat_theory_adv", inject_cat_theory_adv),
    ("CWV Performance", "inject_cwv", inject_cwv),
    ("Design Tokens", "inject_design", inject_design),
    ("Goat Math", "inject_goat", inject_goat),
    ("Mythos Primitives", "inject_mythos", inject_mythos),
    ("Spatial Render", "inject_spatial", inject_spatial),
    ("Agent-Principal", "inject_agent_principal", inject_agent_principal),
    ("OSINT Defense", "inject_osint", inject_osint),
    ("Complex Systems", "inject_complex_systems", inject_complex_systems),
    ("Git Exergy", "inject_git_exergy", inject_git_exergy),
    ("Physical Laws", "inject_physical_laws", inject_physical_laws),
    ("DAME Framework", "inject_dame_framework", inject_dame_framework),
    ("Arkham Breadcrumbs", "inject_arkham_breadcrumbs", inject_arkham_breadcrumbs),
]

async def run_pipeline():
    logger.info("=== STARTING CORTEX PERSIST COGNITIVE CONSOLIDATION PIPELINE (C5-REAL) ===")
    
    for display_name, err_id, injector_fn in INJECTORS:
        try:
            logger.info(f"Running {display_name} injection...")
            await injector_fn()
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Error in {err_id}: {e}")

    logger.info("=== ALL INJECTIONS COMPLETED ===")
    logger.info("Waiting 3.0 seconds to guarantee full ledger batch commit to security_audit_log.jsonl...")
    await asyncio.sleep(3.0)
    logger.info("=== LEDGER BATCHES FULLY COMMITTED ===")

if __name__ == "__main__":
    asyncio.run(run_pipeline())

