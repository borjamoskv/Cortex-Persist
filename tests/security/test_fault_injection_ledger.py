import asyncio
import os
import tempfile
import pytest
from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.database.core import connect_async_ctx, connect

@pytest.mark.asyncio
async def test_ledger_tamper_evident_corruption_detection():
    # 1. Setup secure environment
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_ledger.db")
    
    # 2. Initialize Ledger and write valid transactions
    async with connect_async_ctx(db_path) as conn:
        conn._conn.authorize_causal_writes()
        ledger = EnterpriseAuditLedger(conn)
        await ledger.ensure_table()
        
        id1 = await asyncio.wait_for(ledger.log_action("tenant_1", "system", "actor_1", "CREATE", "fact:1001"), timeout=5.0)
        id2 = await asyncio.wait_for(ledger.log_action("tenant_1", "system", "actor_1", "UPDATE", "fact:1001"), timeout=5.0)
        id3 = await asyncio.wait_for(ledger.log_action("tenant_1", "system", "actor_1", "DELETE", "fact:1001"), timeout=5.0)
        
        # Force flush and close
        await asyncio.sleep(0.1)
        await ledger.close()
    
    # 3. Verify clean state
    async with connect_async_ctx(db_path) as conn2:
        conn2._conn.authorize_causal_writes()
        ledger_verify = EnterpriseAuditLedger(conn2)
        await ledger_verify.ensure_table()
        verify_result = await ledger_verify.verify_chain()
        
        assert verify_result.get("status") == "verified", f"Initial verification failed: {verify_result}"
        await ledger_verify.close()
    
    # 4. Inyección de Corrupción (Mutilación Física en Caliente)
    # Atacante interno modifica la base de datos saltándose el Ledger
    conn_sync = connect(db_path)
    conn_sync.authorize_causal_writes()
    cursor = conn_sync.cursor()
    
    # Cambiamos "CREATE" por "EXFILTRATE" para simular un ataque
    cursor.execute("UPDATE security_audit_log SET action = 'EXFILTRATE' WHERE audit_id = ?", (id1,))
    conn_sync.commit()
    conn_sync.close()
    
    # 5. Comprobar Tolerancia Bizantina
    async with connect_async_ctx(db_path) as conn3:
        conn3._conn.authorize_causal_writes()
        ledger_tampered = EnterpriseAuditLedger(conn3)
        await ledger_tampered.ensure_table()
        
        tampered_result = await ledger_tampered.verify_chain()
        
        # El sistema debe detectar la ruptura de la cadena Merkle o la falsificación de la firma
        assert tampered_result.get("status") == "tampered", "El Ledger no detectó la mutilación física."
        assert tampered_result.get("corrupted_audit_id") == id1, "No se identificó el nodo exacto de la corrupción."
        await ledger_tampered.close()


