# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import pytest
from fastapi import HTTPException

from cortex.routes.facts import _fact_data as fact_route_data
from cortex.routes.memories import _fact_data as memory_route_data


class _UnsupportedFact:
    pass


def test_facts_fact_data_fails_fast_on_unsupported_shape() -> None:
    with pytest.raises(HTTPException, match="Unsupported fact payload type"):
        fact_route_data(_UnsupportedFact())


def test_memories_fact_data_fails_fast_on_unsupported_shape() -> None:
    with pytest.raises(HTTPException, match="Unsupported fact payload type"):
        memory_route_data(_UnsupportedFact())
