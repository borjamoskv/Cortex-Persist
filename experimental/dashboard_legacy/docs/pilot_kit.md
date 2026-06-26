# Cortex-Persist Pilot Kit & Sales Demo

This guide provides exactly what you need to demonstrate the core value of **Cortex-Persist**: autonomous cryptographic assurance for AI Agents.

## 1. The Core Demo (2 Minutes)
The canonical demo runs completely via a single terminal script. It abstracts away all the complexity of the full 56-skill swarm and strictly visualizes:
1. Creating Tamper-Evident Memory
2. Intentionally Breaking Integrity (Hacking the Database)
3. Falsation Engine Auto-Detection & Report Export

### Running the Demo
Open your terminal in the repository root and execute:

```bash
cd demo
python3 demo_canonical.py
```

### Walkthrough Narrative (Your Script)
- **Phase 1 (Autonomous Decision Registry):** "Our agent identifies a critical vulnerability in the target bounty and makes a massive payout decision. Notice how Cortex intercepts this and records the decision to the WAL ledger, generating an immutable VSA (Vector Symbolic Architecture) signature."
- **Phase 2 (Integrity Verification):** "Cortex continuously reads its edge hashes to ensure what the AI remembers hasn't been selectively poisoned."
- **Phase 3 (Tamper-Evident Trap):** "Now, let's play the attacker. They manage to get SQL access and alter the destination wallet address directly to redirect the ETH. A traditional Agentic logging platform would not know the DB was injected from outside."
- **Phase 4 (Audit Export):** "When Cortex checks the state again or attempts a read... boom. The C5-REAL Integrity check fails. We export precisely which memory blocks were manipulated into a secure audit report."

***

## 2. Setting Up an Onsite Pilot

When deploying Cortex for a Pilot client:
1. Ensure `cortex-db` and the Rust native binaries are accessible in the `engine` directory.
2. Initialize testing via `demo_canonical.py`, handing over the resulting `cortex_audit_evidence.json` as a Proof of Concept of how their infrastructure will secure AI outputs.
3. Validate policy limits using the Web Dashboard.
