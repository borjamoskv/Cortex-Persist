import asyncio
import os
import signal
import sqlite3
import sys
import multiprocessing
import pytest
from unittest.mock import patch

@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test_atomic_ledger.db"
    yield str(path)
    if path.exists():
        path.unlink()

async def setup_ledger(db_path):
    import aiosqlite
    from cortex.database.core import connect_async
    from cortex.audit.ledger import EnterpriseAuditLedger

    conn = await connect_async(db_path)
    await conn.execute("CREATE TABLE IF NOT EXISTS business_data (id INTEGER PRIMARY KEY, value TEXT)")
    await conn.commit()

    ledger = EnterpriseAuditLedger(conn)
    await ledger.ensure_table()
    return conn, ledger

@pytest.mark.asyncio
async def test_property_a_commit_persists_both(db_path):
    """Propiedad A (Happy Path): commit de negocio + log_action -> Ambos persisten."""
    from cortex.database.core import causal_write
    conn, ledger = await setup_ledger(db_path)
    
    with causal_write(conn):
        await conn.execute("INSERT INTO business_data (value) VALUES ('secret_operation')")
        await ledger.log_action(
            tenant_id="tenant_1",
            actor_role="admin",
            actor_id="user_123",
            action="CREATE_SECRET",
            resource="secret_operation"
        )
        await conn.commit()
    
    await ledger.close()
    await conn.close()
    
    check_conn = sqlite3.connect(db_path)
    assert check_conn.execute("SELECT count(*) FROM business_data").fetchone()[0] == 1
    assert check_conn.execute("SELECT count(*) FROM security_audit_log").fetchone()[0] == 1
    check_conn.close()

@pytest.mark.asyncio
async def test_property_b_exception_intermediate(db_path):
    """Propiedad B: Excepción antes del commit -> Ninguno persiste."""
    from cortex.database.core import causal_write
    conn, ledger = await setup_ledger(db_path)
    
    try:
        with causal_write(conn):
            await conn.execute("INSERT INTO business_data (value) VALUES ('secret_operation')")
            await ledger.log_action(
                tenant_id="tenant_1",
                actor_role="admin",
                actor_id="user_123",
                action="CREATE_SECRET",
                resource="secret_operation"
            )
            raise ValueError("Artificial Exception")
            await conn.commit()
    except ValueError:
        pass
        
    await ledger.close()
    await conn.close()
    
    check_conn = sqlite3.connect(db_path)
    assert check_conn.execute("SELECT count(*) FROM business_data").fetchone()[0] == 0
    assert check_conn.execute("SELECT count(*) FROM security_audit_log").fetchone()[0] == 0
    check_conn.close()

@pytest.mark.asyncio
async def test_property_c_rollback(db_path):
    """Propiedad C: Rollback explícito -> Ninguno persiste."""
    from cortex.database.core import causal_write
    conn, ledger = await setup_ledger(db_path)
    
    with causal_write(conn):
        await conn.execute("INSERT INTO business_data (value) VALUES ('secret_operation')")
        await ledger.log_action(
            tenant_id="tenant_1",
            actor_role="admin",
            actor_id="user_123",
            action="CREATE_SECRET",
            resource="secret_operation"
        )
        await conn.rollback()
        
    await ledger.close()
    await conn.close()
    
    check_conn = sqlite3.connect(db_path)
    assert check_conn.execute("SELECT count(*) FROM business_data").fetchone()[0] == 0
    assert check_conn.execute("SELECT count(*) FROM security_audit_log").fetchone()[0] == 0
    check_conn.close()


def _run_crash_target(db_path):
    async def target():
        import aiosqlite
        from cortex.database.core import connect_async, causal_write
        from cortex.audit.ledger import EnterpriseAuditLedger

        conn = await connect_async(db_path)
        await conn.execute("CREATE TABLE IF NOT EXISTS business_data (id INTEGER PRIMARY KEY, value TEXT)")
        await conn.commit()

        ledger = EnterpriseAuditLedger(conn)
        await ledger.ensure_table()
        
        loop = asyncio.get_running_loop()
        # Schedule a SIGKILL right after log_action but before commit
        loop.call_later(0.01, lambda: os.kill(os.getpid(), signal.SIGKILL))

        with causal_write(conn):
            await conn.execute("INSERT INTO business_data (value) VALUES ('secret_operation')")
            
            try:
                await ledger.log_action(
                    tenant_id="tenant_1",
                    actor_role="admin",
                    actor_id="user_123",
                    action="CREATE_SECRET",
                    resource="secret_operation"
                )
            except Exception:
                pass
                
            await asyncio.sleep(0.05)
            await conn.commit()

    asyncio.run(target())

def test_property_d_crash_consistency(db_path):
    """Propiedad D: Cierre inesperado (SIGKILL) antes del commit -> Consistencia estricta (0 y 0)."""
    p = multiprocessing.Process(target=_run_crash_target, args=(db_path,))
    p.start()
    p.join()
    
    check_conn = sqlite3.connect(db_path)
    b_count = check_conn.execute("SELECT count(*) FROM business_data").fetchone()[0]
    a_count = check_conn.execute("SELECT count(*) FROM security_audit_log").fetchone()[0]
    check_conn.close()
    
    # Ambos deben ser 0 porque la transacción no se cerró.
    assert b_count == 0
    assert a_count == 0
