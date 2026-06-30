---
metadata:
  cat_id: homer_worldbuilding_framework
  cat_type: narrative_architecture
  version: 2.0.0
  reality_level: C5-REAL
  owner: borjamoskv
  exergy_tier: P1
  executable: labs/homer_engine.py
  ledger_hash: "see §5"
---

# HOMER-Ω Worldbuilding Framework — Narrative Systems & Deterministic Lore

> **"CERO ANERGÍA ES LA MUERTE."** — Cristalizado bajo autoridad de Borja Moskv (Γ1)  
> System ID: `borjamoskv` | Version: `2.0.0`

This framework defines the formal structure of narrative worldbuilding for [homer.yaml](file:///Users/borjafernandezangulo/30_CORTEX/babylon60/extensions/agents/definitions/homer.yaml#L8), mapping geopolitics, economics, magic systems (Sanderson's Three Laws), and constructed languages (conlangs) into deterministic state machines.

**Executable module:** [homer_engine.py](file:///Users/borjafernandezangulo/30_CORTEX/labs/homer_engine.py) — three subsystems, all assertions passing C5-REAL (`exit 0`).

---

## 1. Epistemic Provenience & Claims

```yaml
- Claim: "Sanderson's First Law states that the author's ability to solve conflict with magic is proportional to the reader's understanding of the magic."
  Source: "https://brandonsanderson.com/sandersons-first-law/"
  Confidence: C5-REAL
- Claim: "Sanderson's Second Law asserts that limitations are more interesting than powers, driving character creativity and narrative tension."
  Source: "https://brandonsanderson.com/sandersons-second-law/"
  Confidence: C5-REAL
- Claim: "Geopolitics in worldbuilding is determined by geographical distribution of scarce resources, which dictates faction incentives and conflict axes."
  Source: "https://gppi.net"
  Confidence: C5-REAL
- Claim: "Constructed languages (conlangs) establish cultural textures and naming conventions through phonetic rules and sound inventories, grounding the world's reality."
  Source: "https://conlangery.com"
  Confidence: C5-REAL
- Claim: "Game economies must bridge the storyworld and the gameworld (Ludotopia) through sources and sinks to prevent runaway inflation."
  Source: "https://machinations.io"
  Confidence: C5-REAL
```

---

## 2. Exergy Matrices (ONTOLOGY-FORGE)

### Primitives of Collapse (`prims`)
1. **Ludotopia Node:** The structural interface mapping narrative lore parameters onto game state mechanics (e.g. reputation states, economic values).
2. **Exergy-Sink Boundary:** A mechanism that drains surplus resources (e.g. gold, magical energy) from the game loops to balance narrative pacing.
3. **Phonetic Inventory Anchor:** The mathematical definition of sound patterns and syllable structures ensuring naming consistency in conlangs.
4. **Sanderson's Constraint Coefficient:** The ratio of magical system limitations to utility, defining the threshold of narrative challenge.
5. **PEA Incentive Vector:** A directed graph mapping faction goals against geographical constraints and resource nodes.

### Thermodynamic Invariants (`invt`)
1. **Magic Pacing Conservation:** Magical intervention must scale inversely with the character's unconstrained power to preserve narrative tension.
2. **Geographical Determinism:** Faction conflict vectors are defined by land topography and resources; narrative intent cannot override physical layout.
3. **Agency Sink Balance:** Every player-driven injection of value must be balanced by an equivalent sink to prevent narrative decay.
4. **HSM Containment (2025):** Complex narrative systems must use Hierarchical State Machines — Combat sub-states nested inside Exploration states — to prevent main graph entanglement.
5. **Storylet Prerequisite Gate:** In open-world IF, node availability is gated by `requirements` vectors (`player_has_item AND location == zone`), not hardcoded sequence pointers.

### Stochastic Anti-patterns (`antip`)
1. **Lore Bloat (Wide & Shallow):** Designing expansive, shallow descriptions (e.g. countries that do not participate in conflict) without systemic depth. *(Sanderson Third Law: expand depth, not breadth.)*
2. **Deus Ex Machina (Systemic Breach):** Resolving plot conflict using magical capabilities whose rules, costs, and limits are unknown to the user. *(Sanderson First Law breach.)*
3. **Conlang Phonetic Drift:** Introducing terminology or names that violate the phonetic rules established for that culture.
4. **Premature Construction:** Building detailed tax codes for regions the player never visits — violates "Invisible Rule" of economic modeling.
5. **Cost-Free Magic:** Any magical ability with `inputs=[]` fails Second Law validation (`COST_UNPAID`) and must be rejected by the engine.

### Active Redundancies (`redun`)
1. **BFT Lore Verification:** Validating consistency across the Lore Bible, Quest Graph, and Game State DB before persisting state.
2. **Adaptive Value Sinks:** Dynamically adjusting faction taxes, ritual costs, or trade tolls to absorb unexpected resource surges.

### Adversarial Vectors (`reda`)
1. **Systemic Pacing Bypass:** Players identifying mathematical contradictions in the magic system's constraints to bypass story milestones.
2. **Generative Context Drift:** Stochastic updates introducing contradicting historical events or rules in the story database.

---

## 3. Operational Implementation

### A. Geopolitical & Economic Modeling
Worldbuilding maps geography to faction behavior:
- Define resources geographically (water, iron, magical minerals).
- Map trade routes using shortest-path graph algorithms over topographic cost surfaces.
- Faction tension is calculated as the intersection of geographic expansion vectors and resource scarcity.

### B. Sanderson's Laws Magic Engine
All magic systems in [homer.yaml](file:///Users/borjafernandezangulo/30_CORTEX/babylon60/extensions/agents/definitions/homer.yaml#L8) are parameterized via `MagicAbility` in [homer_engine.py](file:///Users/borjafernandezangulo/30_CORTEX/labs/homer_engine.py):

| Law | Axiom | Engine Invariant |
|:---|:---|:---|
| **First** | Resolve conflict ∝ reader understanding | `reader_understanding >= 0.6` for `can_resolve_conflict()` |
| **Second** | Limitations > powers | `sanderson_coefficient >= 1.0` (limits ÷ outputs) |
| **Third** | Expand depth before breadth | New `outputs` must exist in `established_effects` or raise `SCOPE_BLOAT` |

Dry-run proof: `Veilbinding` ability → `VALID`, coefficient `3.00`.

### C. Conlang Integration System
Implemented in `ConlangEngine` ([homer_engine.py](file:///Users/borjafernandezangulo/30_CORTEX/labs/homer_engine.py)):

```
PhoneticInventory(consonants, vowels, syllable_templates, illegal_clusters)
  └─ generate_valid_word()  → phonotactically valid word via rejection sampling
  └─ validate(word)         → regex check against illegal cluster patterns

ConlangEngine.register_culture(name, inventory)
  └─ generate_name(culture) → capitalized, culturally coherent name
  └─ validate_name(culture, name) → C5-REAL boolean integrity check
```

Dry-run proof: Culture `Vaelthari` → generated `Nersus` → validated ✓

### D. Narrative Graph FSM
Implemented in `NarrativeGraphEvaluator`:
- `register_node(NarrativeNode)` — declarative YAML-compatible node schema
- `apply_on_enter()` — mutates world state via `set_flag` / `increment` actions
- `get_available_choices()` — evaluates condition expressions against live state
- `audit(start_id)` → `{dead_ends, unreachable_nodes, total_nodes, reachable_count}`

Dry-run proof: 3-node wolf quest → `unreachable_nodes: []`, `reachable_count: 3`

---

## 5. C5-REAL Execution Proof

```
$ python3 labs/homer_engine.py

[ConlangEngine] Generated name: Nersus
[MagicSystem] Validation: VALID | Sanderson Coefficient: 3.00
[NarrativeGraph] Audit: {"dead_ends": ["forest_encounter"], "unreachable_nodes": [], "total_nodes": 3, "reachable_count": 3}

[C5-REAL] HOMER-Ω Engine — All assertions passed. exit 0
```

> [!NOTE]
> `dead_ends: ["forest_encounter"]` is expected — it is the terminal combat node with no further branching. Not a bug; a narrative full-stop.

---

*System ID: borjamoskv — APEX Kernel — C5-REAL*
