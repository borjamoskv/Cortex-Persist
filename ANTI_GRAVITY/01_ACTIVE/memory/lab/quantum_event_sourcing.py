import random
import time


class ProbabilisticEventStore:
    def __init__(self):
        self.superposed_events = []
        self.deterministic_log = []

    def write_superposition(self, event_id: str, probable_states: dict):
        """
        Stores an event as a probability matrix instead of a deterministic value.
        No database locks are acquired, allowing infinite write concurrency.
        """
        self.superposed_events.append(
            {"id": event_id, "states": probable_states, "collapsed": False, "final_state": None}
        )
        print(f"[W] Write O(1): Event {event_id} stored in superposition. (Locks: 0)")

    def _collapse_wavefunction(self, event):
        """Forces deterministic resolution upon observation based on probability vector."""
        if not event["collapsed"]:
            states = list(event["states"].keys())
            probabilities = list(event["states"].values())
            # Collapse mechanism
            resolved_state = random.choices(states, weights=probabilities, k=1)[0]
            event["collapsed"] = True
            event["final_state"] = resolved_state
            self.deterministic_log.append((event["id"], resolved_state))
            return resolved_state
        return event["final_state"]

    def observe(self, query_context: str):
        """
        Reading the database acts as an observation, collapsing all pending superposed states
        into a deterministic reality for the observer.
        """
        print(f"\n[!] OBSERVATION TRIGGERED BY: {query_context}")
        print("[!] Collapsing system wavefunction...")
        time.sleep(0.5)  # Simulating compute cost of observation

        results = []
        for event in self.superposed_events:
            state = self._collapse_wavefunction(event)
            results.append((event["id"], state))
        return results


if __name__ == "__main__":
    db = ProbabilisticEventStore()

    print("--- QUANTUM EVENT SOURCING PROTOTYPE (C5-REAL) ---\n")

    # High concurrency writes with no locking
    db.write_superposition("TX_1001", {"COMMITTED": 0.99, "ROLLBACK": 0.01})
    db.write_superposition("TX_1002", {"COMMITTED": 0.85, "ROLLBACK": 0.15})
    db.write_superposition("TX_1003", {"COMMITTED": 0.90, "ROLLBACK": 0.10})

    print("\n[?] Database state is currently a probability matrix.")
    print("[?] No deterministic reality exists yet. Writes accept infinite concurrency.\n")

    # Read triggers collapse
    observed_state = db.observe("Billing_Aggregator_Cron")

    print("\n[✓] Wavefunction Collapsed. Deterministic Reality Resolved:")
    for tx_id, state in observed_state:
        print(f"  -> {tx_id}: {state}")
