import sys
import asyncio
from persistence import LedgerManager
from k0_swarm_node import HardwareAggressor

async def test_reconciliation():
    ledger = LedgerManager()
    
    # Force bankruptcy
    current_yield = ledger.get_total_yield()
    print(f"Current yield: {current_yield}")
    
    # Introduce deficit if not already bankrupt
    if current_yield >= 0:
        deficit = -(current_yield + 35957.0)
        ledger.append(action="BURN_OUT", vector_id="SIMULATED_TEST", yield_amount=deficit)
        import time
        time.sleep(1.5) # Wait for signer thread
        new_yield = ledger.get_total_yield()
        print(f"Induced bankruptcy. New yield: {new_yield}")
        
    # Run HardwareAggressor evaluate_expansion which should trigger reconcile
    hardware = HardwareAggressor(ledger)
    
    # Setting threshold low so it expands if positive
    hardware.expansion_threshold = 0.5 
    
    print("Evaluating expansion...")
    expanded = await hardware.evaluate_expansion()
    print(f"Expanded? {expanded}")
    
    # Wait for reconciliation and next operations
    time.sleep(1.5)
    final_yield = ledger.get_total_yield()
    print(f"Final Yield: {final_yield}")
    
    ledger.close()

if __name__ == "__main__":
    asyncio.run(test_reconciliation())
