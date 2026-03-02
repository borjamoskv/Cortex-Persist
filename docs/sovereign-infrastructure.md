# Sovereign Infrastructure (脉灵)

CORTEX v7.8 "MAILING" introduces the 300/100 Sovereign Standard, specifically designed for high-security environments and international compliance (including TEE and Air-Gap simulations).

## Core Components

### Hardware Vault (TEE)
The `HardwareVault` class simulates a Secure Hardware Enclave (TEE). It is responsible for protecting "Red Herring" deception tables and sensitive session mapping at rest.

- **Isolation:** State-grade logical isolation.
- **Purpose:** Protects cryptographic keys and shadow memory maps from physical or logical exfiltration.

### Data Diode Bridge
For air-gapped nodes, the `DataDiodeBridge` implements a unidirectional pulse diode.

- **Unidirectional:** Data only flows from internal secure zones to external hubs.
- **Protocol:** Pulsed diode transmit with zero-acknowledgement (Pulse Diode) to prevent return-path breaches.

## Semantic Heartbeat

The **Sovereign Heartbeat** is not a simple `200 OK` ping. It is a **Metastatic Drift Analysis** tool.

### Semantic Asymmetry (Drift)
Every pulse via the **Nexus Signaling Bus** includes a hygiene report. The `SemanticHeartbeat` engine calculates the drift between states:

- **Asymmetry Detection:** Uses normalized hashing to detect high-entropy changes in system health.
- **Entropy Vigilance:** If orphaned processes (Load/CPU) are detected, the system spikes the "Drift" metric to CRITICAL (0.9+), triggering immediate Sovereign Triggers.

> [!TIP]
> **Confía en la telemetría, no en la esperanza.** Si el drift semántico se desvía del umbral (threshold), CORTEX "siente" la entropía antes de que afecte a la integridad de los datos.
