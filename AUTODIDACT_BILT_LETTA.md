# AUTODIDACT-RESEARCH-Ω: STATEFUL AGENT FLEETS IN LOYALTY COMMERCE (BILT & LETTA)

**Reality Level:** `C5-REAL` (Epistemic Synthesis)
**Vector:** Interdisciplinary Knowledge Transfer (Stateful Agent Frameworks / Loyalty Systems -> Scale-Out Personalization Engine)
**Target:** Letta (MemGPT) + Bilt Rewards Personalized Recommendation Engine (scale of millions of agents)

## 1. Isomorphic Extraction (Dejargonization)
*   **Letta Core Memory (System / User blocks):** Stateful, read-write working memory directly in the LLM context window. -> *Active user profiles and current loyalty goals (e.g., "saving for a flight to Tokyo", "preferred dining days") kept in the hot-context window for immediate inference without vector retrieval.*
*   **Archival & Recall Memory (Vector / Database blocks):** Unlimited history loaded via paging or search query tools. -> *Historical transaction logs, past redemption events, and point-earning history cached in a cold-storage document store or vector database, queryable on demand.*
*   **Agent-per-User Architecture:** Running one virtual stateful agent for every user in the database. -> *A massive swarm of lightweight state machines ($10^6+$ instances), where each instance encapsulates one consumer's behavioral trajectory and point accumulation strategy.*
*   **Bilt Points & Merchant Network (Dining/Rent/Travel):** The loyalty mechanism that translates everyday spend (specifically rent and dining) into high-value redemption actions. -> *The state transition triggers that feed the agent's utility function, where the agent constantly computes optimal earn-and-burn routes for a specific user.*
*   **Personalized Recommendation Loop (Earn -> Burn optimization):** Selecting merchants, travel deals, or rent points redemption opportunities based on user profile. -> *The policy optimization phase where the user's agent evaluates available merchant offers against the user's active goals and constraints.*

## 2. Topological Mapping (Letta/Bilt vs CORTEX-Persist)
*   **The Letta Bottleneck (Centralized Relational DB):** Letta stores agent state (including historical recall logs and system prompts) in a centralized Postgres database. For "millones de agentes", this creates a high-latency database bottleneck during state synchronization (de/serialization of Agent State JSON and context loading). Every agent step triggers multiple SELECT/UPDATE operations.
*   **The CORTEX-Persist Causal Alternative (Decentralized SQLite WAL):** Instead of a single gargantuan database, CORTEX-Persist scales horizontally by using **SQLite-per-User (Tenant Isolation)**. Since each loyalty user only interacts with their own history, we store each agent's state in an isolated SQLite database file. This eliminates cross-tenant locks, reduces latency to $<2\text{ms}$ read/write, enables WAL mode parallelism, and simplifies backups (archiving individual user DBs).
*   **Causal Event Mesh vs REST Polling:** Letta agents are usually invoked via REST calls or active loop managers. In a commerce platform like Bilt, agents should sleep until a transaction event occurs. CORTEX-Persist uses a reactive, event-driven pattern-matching mechanism (MHC mesh), waking up the specific user agent only when a spend event (e.g., dining checkout, rent paid) or target reward alert is published to the event bus.

## 3. Structural Hole Detection
*   **Current Constraint (Context Load Cost at scale):** Loading Letta agents requires rebuilding their full state (system prompt, core memory blocks, recent messages) into the LLM context. At millions of users, running this continuously represents extreme token waste (Anergía).
*   **CORTEX-Persist Solution (Vector/AST Pruning & State Compilation):** Instead of passing the raw history, CORTEX-Persist compiles user state into a compressed **Epistemic State Token** (a highly dense YAML summary + recent event ledger). Archival logs are indexed via local `sqlite-vec` vectors, queryable only when the agent explicitly requests it. This keeps the active context window $<1.5\text{k}$ tokens instead of $8\text{k}-16\text{k}$.

## 4. Hypothesis Forge (Falsifiable Prediction)
**Hypothesis [H-BILT-LETTA-01]: Isolated SQLite WAL Sharding for Stateful Fleets**
*   **Claim:** Reemplazar una base de datos Postgres centralizada de Letta por un esquema de bases de datos SQLite fragmentadas por usuario (SQLite-per-User) bajo CORTEX-Persist reducirá la latencia de sincronización de estado de los agentes en un >85% y recortará los costes de infraestructura de base de datos en un >60%, manteniendo una consistencia transaccional absoluta y aislamiento de datos a nivel de tenant.
*   **Proof Conditions:**
    *   *Base:* Una simulación de 10,000 agentes concurrentes realizando actualizaciones de estado (mensajes de chat, inserción de hechos y consultas a memoria archival) contra una instancia centralizada de Letta Postgres.
    *   *Medición:* Latencia media de lectura/escritura de estado, consumo de CPU/RAM de la base de datos, y transacciones por segundo (TPS) antes de degradación.
    *   *Confianza:* C5-REAL (Implementable mediante el almacenamiento local de cortex y SQLite WAL sharding).
