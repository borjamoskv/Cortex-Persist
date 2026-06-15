import pytest
from cortex.guards.contradiction_guard import _jaccard

def test_jaccard():
    assert _jaccard({"a"}, {"a"}) == 1.0
