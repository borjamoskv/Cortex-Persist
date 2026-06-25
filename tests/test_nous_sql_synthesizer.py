# [C5-REAL] Exergy-Maximized
"""Tests for NOUS SQL Synthesizer."""

from cortex.extensions.nous.models import NousAST, NousMetadata, NousOperation
from cortex.extensions.nous.sql_synthesizer import SQLSynthesizer


def test_sql_synthesizer() -> None:
    ast = NousAST(
        metadata=NousMetadata(version="1.0", author="test", description="test"),
        ensures=[],
        operations=[
            NousOperation(
                type="create_table",
                target="users",
                sql="CREATE TABLE users (id INT PRIMARY KEY)",
                rollback_sql="DROP TABLE users",
            ),
            NousOperation(
                type="unknown_op",
                target="data",
                sql="SELECT 1",
                rollback_sql=None,
            ),
        ],
        invariants=[],
    )

    migrations = SQLSynthesizer.synthesize(ast)

    assert len(migrations) == 2

    m1 = migrations[0]
    assert m1.op == "create_table"
    assert m1.table == "users"
    assert m1.sql_up == "CREATE TABLE users (id INT PRIMARY KEY)"
    assert m1.sql_down == "DROP TABLE users"

    m2 = migrations[1]
    assert m2.op == "raw_sql"
    assert m2.table == "data"
    assert m2.sql_up == "SELECT 1"
    assert m2.sql_down == ""
