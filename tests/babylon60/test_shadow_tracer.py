# [C5-REAL] Exergy-Maximized
"""
Tests for the Wave 2 Shadow Resolver and Import Tracer.
"""

import os
import sys
import json
import pytest
from pathlib import Path

# Ensure the project root is in sys.path
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from babylon60.shadow_tracer import enable_tracer, disable_tracer


def test_shadow_tracer_collection():
    # Enable tracer in default "present" mode
    tracer = enable_tracer(mode="present")

    try:
        # Import something that triggers the tracer
        import babylon60.core

        # Verify that it is recorded in the import graph
        # The key is likely this module's name
        caller = __name__
        assert caller in tracer.imports

        # Verify the exported compatibility graph
        report_path = _REPO_ROOT / "test_compatibility_graph.json"
        report = tracer.export_compatibility_graph(str(report_path))

        assert report_path.exists()
        assert "metrics" in report
        assert "import_graph" in report

        # Cleanup report file
        if report_path.exists():
            os.remove(report_path)

    finally:
        disable_tracer()


def test_cycle_detection():
    tracer = enable_tracer(mode="present")
    try:
        # Clear existing to test cleanly
        tracer.imports.clear()

        # Inject a cycle: A -> B -> A
        tracer.record_import("babylon60.a", "babylon60.b")
        tracer.record_import("babylon60.b", "babylon60.a")

        cycles = tracer.detect_cycles(collapsed=False)
        assert len(cycles) > 0
        assert "babylon60.a" in cycles[0]
        assert "babylon60.b" in cycles[0]

    finally:
        disable_tracer()


def test_cycle_detection_under_collapse():
    tracer = enable_tracer(mode="present")
    try:
        tracer.imports.clear()

        # Inject relationship: babylon60.a -> cortex.a (which is legacy)
        # and cortex.a -> babylon60.a (which would collapse to babylon60.a -> babylon60.a)
        # Or a more realistic cycle:
        # babylon60.service -> cortex.engine -> babylon60.service
        # Under collapse:
        # babylon60.service -> babylon60.engine -> babylon60.service (cycle!)
        tracer.record_import("babylon60.service", "cortex.engine")
        tracer.record_import("cortex.engine", "babylon60.service")

        # No cycle should be detected under uncollapsed
        cycles_uncollapsed = tracer.detect_cycles(collapsed=False)
        # Wait, actually "babylon60.service" -> "cortex.engine" -> "babylon60.service" IS a cycle in the original graph too!
        # Let's design a cycle that ONLY appears after collapse:
        # Node A: cortex.engine (collapses to babylon60.engine)
        # Node B: babylon60.engine
        # Edge 1: babylon60.api -> cortex.engine
        # Edge 2: babylon60.engine -> babylon60.api
        # In original graph: babylon60.api -> cortex.engine, babylon60.engine -> babylon60.api (no cycle)
        # In collapsed graph: babylon60.api -> babylon60.engine, babylon60.engine -> babylon60.api (cycle!)
        tracer.imports.clear()
        tracer.record_import("babylon60.api", "cortex.engine")
        tracer.record_import("babylon60.engine", "babylon60.api")

        cycles_uncollapsed = tracer.detect_cycles(collapsed=False)
        assert len(cycles_uncollapsed) == 0

        cycles_collapsed = tracer.detect_cycles(collapsed=True)
        assert len(cycles_collapsed) > 0
        assert "babylon60.api" in cycles_collapsed[0]
        assert "babylon60.engine" in cycles_collapsed[0]

    finally:
        disable_tracer()
