# [C5-REAL] Exergy-Maximized
"""NOUS SQL Synthesizer - Transforms AST into executable MigrationOperations

Reality Level: C5-REAL
"""

from .models import MigrationOperation, NousAST


class SQLSynthesizer:
    @staticmethod
    def synthesize(ast: NousAST) -> list[MigrationOperation]:
        """
        Maps a declarative NousAST into an ordered list of MigrationOperations
        ready for the DryRun engine.
        """
        migrations = []

        valid_ops = {
            "create_table",
            "alter_table",
            "drop_table",
            "create_index",
            "drop_index",
            "add_column",
            "drop_column",
            "alter_column",
            "add_constraint",
            "drop_constraint",
            "create_function",
            "drop_function",
            "create_trigger",
            "drop_trigger",
            "create_view",
            "drop_view",
            "grant",
            "revoke",
            "raw_sql",
        }

        for op in ast.operations:
            op_type = op.type if op.type in valid_ops else "raw_sql"

            # Identify specific constraints from AST if needed, for now just empty list
            mig = MigrationOperation(
                op=op_type,  # type: ignore
                table=op.target,
                sql_up=op.sql,
                sql_down=op.rollback_sql or "",
                constraints=[],
            )
            migrations.append(mig)

        return migrations
