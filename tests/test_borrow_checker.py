import pytest
import asyncio
from cortex.engine.borrow_checker import LogicalBorrowChecker, StateDriftError

@pytest.mark.asyncio
async def test_logical_borrow_checker_prevents_semantic_race():
    checker = LogicalBorrowChecker()
    
    # 1. Múltiples Shared Borrows (&State) son permitidos
    await checker.acquire_shared("ledger_state")
    await checker.acquire_shared("ledger_state")
    assert checker._shared_borrows["ledger_state"] == 2
    
    # 2. Mut Borrow (&mut State) es bloqueado por Shared Borrows
    with pytest.raises(StateDriftError, match="Violación de Exclusividad"):
        # Timeout de 0.1s para acelerar el test
        await checker.acquire_mut("ledger_state", timeout_sec=0.1)
        
    # 3. Liberación de Shared Borrows
    await checker.release_shared("ledger_state")
    await checker.release_shared("ledger_state")
    
    # 4. Ahora el Mut Borrow es exitoso
    await checker.acquire_mut("ledger_state")
    assert "ledger_state" in checker._mut_borrows
    
    # 5. Nuevo Shared Borrow es bloqueado por Mut Borrow
    with pytest.raises(StateDriftError, match="Existe un '&mut' activo"):
        await checker.acquire_shared("ledger_state", timeout_sec=0.1)
        
    # 6. Liberación de Mut Borrow
    await checker.release_mut("ledger_state")
    
    # Terminado limpio
    assert len(checker._mut_borrows) == 0
    assert "ledger_state" not in checker._shared_borrows
