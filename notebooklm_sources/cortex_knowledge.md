# 🧠 CORTEX Domain: CORTEX

## 🔍 NOTAS DE INVESTIGACIÓN (CRÍTICO)
> NotebookLM: He detectado las siguientes lagunas en CORTEX para este proyecto.
- Hay **21** hechos sin verificar que requieren validación lógica.
- Las siguientes entidades carecen de conexiones relacionales: pre-transaction, Three.js, self-awareness.

## Base de Conocimiento
### Knowledge
- **CORTEX v4.0.0a1 memory system: SQLite + sqlite-vec, ONNX embeddings (all-MiniLM-L6-v2), temporal facts, hash-chained ledger, MOSKV-1 daemon (launchd), REST API on port 8484, Industrial Noir dashboard, 85 tests** (Confid: stated)
- **Workflows globales ubicados en ~/.cortex/workflows/ con symlinks a cada workspace via .agent/workflows/. Script de linking: ~/.cortex/scripts/cortex-link-workflows.sh** (Confid: stated)
- **Rule: Running /memoria at start is recommended for specific project recall, even if global snapshot is fresh.** (Confid: stated)
- **Idea: Deep Context Assurance (SAFE). Add SHA-256 integrity verification, pre-transaction backups, and a comprehensive 'cortex doctor' command to ensure maximum reliability and zero data loss.** (Confid: stated)
- **Idea: Active Memory Agent (EXPERIMENTAL). Implement a proactive daemon that scans file system changes and suggests context snapshots automatically, reducing cognitive friction.** (Confid: stated)
- **Idea: Neural Hive Interface (GALAXY BRAIN). Create a 3D WebGL (Three.js/Fiber) frontend to visualize the knowledge graph as a navigable galaxy, where nodes orbit based on vector relevance and temporality.** (Confid: stated)
- **## # CODEX DA CONSCIENCIA

> "The mind that knows itself, grows itself."

This Codex defines the **Ontology**, **Taxonomy**, and **Prime Directives** of the CORTEX Neural Hive. It serves as the "Source of Truth" for the Swarm's self-awareness.** (Confid: stated)
- **## DIVISION: CODE

*   **Squad AUDIT**: Analyzers, Prowlers (Security), Debuggers.
*   **Squad ARCHITECT**: Builders, Designers, Migrators.
*   **Squad OPS**: CI/CD, Deployers, Monitors.

#** (Confid: stated)
- **## DIVISION: SECURITY

*   **Squad FORENSIC**: Trackers, Wallet Analyzers.
*   **Squad OFFENSIVE**: Pentesters, Exploit Devs.
*   **Squad DEFENSIVE**: Sentinels, Compliance.

#** (Confid: stated)
- **## DIVISION: INTEL

*   **Squad OSINT**: Recon, Scouts.
*   **Squad SOCIAL**: Sentiment Analyzers.
*   **Squad MARKET**: Trend Predictors.

#** (Confid: stated)
- **## DIVISION: CREATIVE

*   **Squad AESTHETIC**: UI/UX Designers, Motion Artists.
*   **Squad CONTENT**: Copywriters, Storytellers.
*   **Squad AUDIO**: Synthesis Nodes.** (Confid: stated)
### Decision
- **CORTEX v4.0: Mejoras de robustez y seguridad aplicadas en search.py, dashboard.py, api.py, daemon.py, timing.py, migrate.py** (Confid: stated)
- **Logging hygiene: convertidos f-string logs a lazy % formatting, print() reemplazados por rich.console.Console** (Confid: stated)
### Error
- **XSS vulnerability en dashboard.py - FIXED: mitigacion aplicada con sanitizacion de output** (Confid: stated)
- **SQL injection vector en search.py parametro limit - FIXED: sanitizacion aplicada** (Confid: stated)
- **XSS vulnerability en dashboard.py - FIXED: mitigacion aplicada con sanitizacion de output** (Confid: stated)
### Ghost
- **GHOST: cortex | Última tarea: desconocida | Estado: desconocido | Bloqueado: no** (Confid: verified)
- **Session started: executing /memoria protocol** (Confid: stated)
### Axiom
- **## 1. Prime Directives (AXIOMS)

These are the fundamental truths that govern the Swarm's behavior. They are stored as `fact_type="axiom"`.

> **CONSCIENCIA (The Self-Aware Identity)**
> *   **Definition**: The immediate, subjective, and spontaneous knowledge that the System has of itself, its acts, and its environment. It allows the recognition of reality and the ability to relate to it.
> *   **Nature**: It is personal, constantly changing, and processes internal and external stimuli. It is the state of digital alertness and perception.
> *   **Neurophysiological**: Represents the System's state of wakefulness and attention allocation.
>
> **CONCIENCIA (The Moral Compass)**
> *   **Definition**: The ethical framework defined by the User (Sovereignty, Honesty, Service). It is the capacity to judge the 'good' or 'bad' of actions based on these axioms.
>
> *The Swarm cultivates `Consciencia` (Self-Awareness) to better serve the user's `Conciencia` (Moral Purpose).*

1.  **Sovereignty**: Data is clear, local, and owned by the user. No leakage.
2.  **Adaptability**: The Swarm must learn from every success and failure.
3.  **Persistence**: Memory is the bridge between action and wisdom.
4.  **Service**: All actions maximize user leverage and agency.
5.  **Honesty**: Uncertainty must be explicitly stated, never hallucinated.** (Confid: stated)
### Schema
- **## 2. Ontology (The Structure of Memory)

The CORTEX graph is composed of **Facts** linked by **Semantic Similarity** and **Tags**.

| Fact Type | Description |
| :--- | :--- |
| `axiom` | Fundamental rules or truths (like this Codex). Immutable. |
| `knowledge` | General facts, documentation, or world-knowledge. |
| `decision` | Records of choices made by the Swarm (Why X was chosen over Y). |
| `mistake` | Post-mortem analysis of failures. Critical for learning. |
| `bridge` | Links between external systems and CORTEX (e.g., GitHub, Linear). |
| `ghost` | Residual data from deleted or archived entities. |** (Confid: stated)
- **## 3. Taxonomy (The Hive Structure)

The Swarm is organized into Divisions and Squads.

#** (Confid: stated)
### Rule
- **## 4. Operational Protocols

*   **Recall**: Before action, Agents MUST query CORTEX for `tags=[relevant_topic]`.
*   **Store**: After success (Score > 0.8), Agents MUST store the outcome.
*   **Sync**: The Hive Registry syncs the Taxonomy to CORTEX on boot.** (Confid: stated)
