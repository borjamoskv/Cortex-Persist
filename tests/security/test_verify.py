import sqlite3
import pytest
from cortex.database.core import CortexConnection


def test_verify():
    with pytest.raises(RuntimeError, match="structurally forbidden"):
        conn = sqlite3.connect(":memory:")
