import sqlite3
import pytest
from babylon60.database.core import CortexConnection
import tests.security.test_physical_claims


def test_verify():
    with pytest.raises(RuntimeError, match="structurally forbidden"):
        conn = sqlite3.connect(":memory:")
