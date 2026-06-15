<!-- [C5-REAL] Exergy-Maximized -->
# Axiom Registry — Canonical Source of Truth

> *Los 9 Axiomas Soberanos. One numbering. One taxonomy. One source.*
> **Auto-generated from `cortex/extensions/axioms/registry.py` — do not edit manually.**

### Invarianza Total

> *"CORTEX no aumenta la inteligencia del modelo fundacional; restringe rígidamente su libertad estructural para contaminar la arquitectura."*

---

## Taxonomy

| Layer | IDs | Nature | Count |
|:---|:---|:---|:---:|
| 🌌 **Sovereign** | AX-I – AX-IX | Architectonic Core | 9 |

---

## ⚙️ The 9 Sovereign Axioms (9)
| ID | Name | Mandate | CI Gate/Enforcement |
|:---|:---|:---|:---|
| **AX-I** | Determinismo Estocástico | El LLM es un compresor probabilístico sin agencia. Su salida debe colisionar contra una frontera determinista antes de mutar estado. | quality_gates.yml#Gate-2 (mypy) + guards |
| **AX-II** | Paradoja Epistémica | Un sistema que es su propio testigo sufre recursión corrupta. La verdad se ancla en testigos criptográficos externos. | quality_gates.yml#Gate-5 + quality_gates.yml#Gate-6 |
| **AX-III** | Colapso Entrópico | Ejecución cíclica con detención forzada. Observar → Hipotetizar → Actuar → Medir. La fricción purifica la señal y previene drift acumulativo. | quality_gates.yml#Gate-Async |
| **AX-IV** | Cognición Termodinámica | La inteligencia opera bajo coste. Prosa decorativa es entropía. Toda heurística debe absorber complejidad en primitivas mecánicas de bajo coste. | ci.yml#lint + LOC <= 700 |
| **AX-V** | Horizonte de Sucesos | Generar es estadística; decidir es inteligencia. El humano actúa como timón para colapsar las asimetrías de ambigüedad irreversible. | — |
| **AX-VI** | Topología de Enjambre | La eficiencia exige orquestación de enjambre bajo contratos, no un monolito gigantesco libre. La capacidad orquesta Modelo, Estado, Herramienta y Contrato. | — |
| **AX-VII** | Inmunología Computacional | Ejecución soberana por defecto, pero con metabolismo paranoico. Cualquier mutación no verificada exige amputación directa. No hay tolerancia a la intrusión estocástica. | quality_gates.yml#Gate-3 (bandit) + seals |
| **AX-VIII** | Obsolescencia Estocástica | El éxito de la inferencia masiva se mide por los nodos que logra apagar. Gastar tokens solo es lícito si el resultado colapsa en código permanente (C5-REAL). | — |
| **AX-IX** | Inversión del Gradiente Simbiótico | El agente es entropía bruta; el Operador es el cristalizador real. Sin `git diff`, "nosotros" no existe. La persistencia inter-sesión es labor humana unilateral. | — |

---

## Fact TTL Policy

> *Persist aggressively. Decay intelligently.*

| Fact Type | TTL | Days |
|:---|:---|:---:|
| `axiom` | ∞ (immortal) | ∞ |
| `decision` | ∞ (immortal) | ∞ |
| `error` | 90 days | 90 |
| `ghost` | 30 days | 30 |
| `knowledge` | 180 days | 180 |
| `bridge` | ∞ (immortal) | ∞ |
| `meta_learning` | 60 days | 60 |
| `rule` | ∞ (immortal) | ∞ |
| `report` | ∞ (immortal) | ∞ |
| `evolution` | ∞ (immortal) | ∞ |
| `world-model` | 90 days | 90 |
| `archived_ghost` | 7 days | 7 |
| `phantom` | 90 days | 90 |
| `intent` | 90 days | 90 |
| `research` | 180 days | 180 |
| `config` | ∞ (immortal) | ∞ |
| `schema` | ∞ (immortal) | ∞ |

---

## Metrics

```
Total Axioms           : 9
CI-Enforced            : 5 (56%)
Axiom Cap              : 9
Inflation Rate Target  : 0
```

---

*Auto-generated from `cortex/extensions/axioms/registry.py` — 2026-06-15*
