<!-- [C5-REAL] Exergy-Maximized -->
---
cat_id: legion
cat_type: workflow
version: 2.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P0
description: "🔱 LEGIØN-1 — Protocolo de Swarm Soberano y Consenso Bizantino en CORTEX"
---

# 🔱 LEGIØN-1 — Sovereign Swarm Protocol v2.0.0

El protocolo `LEGIØN-1` orquesta la ejecución paralela distribuida de subagentes virtuales y aplica un consenso bizantino tolerante a fallos (BFT) ponderado por reputación sobre el almacenamiento persistente **BABYLON-60**.

```yaml
Claim: "El motor CentauroEngine y la clase ByzantineConsensus garantizan un quórum de tolerancia bizantina ponderada de 2/3 para mutaciones atómicas del Ledger."
Proof: { Base: [babylon60/extensions/swarm/centauro_engine.py, babylon60/extensions/swarm/byzantine.py], Range: [Consensus >= 0.67], Confidence: C5-REAL }
```

---

## ⚡ Activación de Misiones (Soberanía Atómica)

La orquestación se invoca mediante el CLI de CORTEX o a través de scripts utilizando la clase [CentauroEngine](file:///Users/borjafernandezangulo/30_CORTEX/babylon60/extensions/swarm/centauro_engine.py#L185).

### 1. Asalto de Construcción (Engage)
```bash
python scripts/legion_strike.py --mission "Despliega reconciliación de logs con firmas Ed25519" --formation GHOST
```

### 2. Auditoría de Seguridad (Storm)
```bash
python scripts/legion_strike.py --mission "Analiza inyecciones de prompt en memoria" --formation PHALANX
```

### 3. Evolución del Enjambre (Evolve)
```bash
python scripts/legion_strike.py --mission "Refactoriza CentauroEngine para admitir gRPC" --cycles 3
```

---

## 🏛️ Catálogo de Formaciones Swarm (`CentauroEngine`)

El enjambre selecciona la formación a través del mapa de clases inmutable `_FORMATION_SIZES`. La especialidad de cada nodo se calcula en tiempo de ejecución de forma determinista mediante el método `_get_specialty(index, formation)`:

| Formación | Agentes | Especialidades (Distribución Determinista) | Propósito Causal |
| :--- | :---: | :--- | :--- |
| **GHOST** | 1 | `[CODE]` fijo | Ejecución monohilo de mínima latencia y cuota API baja. |
| **SPECTRE** | 3 | Rotativo: `[INTEL, CODE, SECURITY]` | Reconocimiento silencioso y recopilación de metadatos. |
| **BLITZ** | 3 | Rotativo: `[INTEL, CODE, SECURITY]` | Ejecución rápida. Fallback automático ante alta adrenalina. |
| **SENTINEL** | 4 | Rotativo: `[INTEL, CODE, SECURITY, DATA]` | Monitorización persistente y liveness audits. |
| **ORACLE** | 5 | Rotativo: `[INTEL, CODE, SECURITY, DATA, INFRA]` | Planificación estratégica y evaluación de blast radius. |
| **SANEDRIN** | 5 | Alternancia estricta sobre 5 especialidades | Quórum Supremo Heterogéneo para decisiones arquitectónicas. |
| **OUROBOROS** | 6 | Rotativo: `[INTEL, CODE, SECURITY, DATA, INFRA, CODE]` | Autopoiesis y auto-mejora recursiva del código base. |
| **PHALANX** | 7 | Alternancia binaria: `[SECURITY, CODE]` | Auditoría de sintaxis y mitigación de vectores adversariales. |
| **PHOENIX** | 8 | Rotativo completo | Auto-sanación del entorno de ejecución y parches automáticos. |
| **CHIMERA** | 10 | Rotativo completo | Síntesis de ideas y resolución de tradeoffs de diseño. |
| **SIEGE** | 12 | Rotativo completo | Descomposición y asimilación de código en grafos complejos. |
| **TESTUDO** | 15 | Alternancia ternaria: `[SECURITY, INFRA, CODE]` | Blindaje de configuraciones, secretos y llaves Ed25519. |
| **HYDRA** | 18 | Rotativo completo | Paralelización masiva sobre múltiples archivos concurrentes. |
| **LEVIATHAN** | 35 | Rotativo completo | Refactorización sistémica masiva de bases de código. |

---

## 🧬 Mecánica de Consenso Bizantino (BFT)

La clase [ByzantineConsensus](file:///Users/borjafernandezangulo/30_CORTEX/babylon60/extensions/swarm/byzantine.py#L23) procesa las propuestas de ejecución simultáneas mediante las siguientes fases:

### 1. Normalización Semántica (AST Unparsing)
Antes del hashing, el contenido se normaliza para evitar discrepancias por espaciados o sintaxis cosmética:
```python
# babylon60/extensions/swarm/byzantine.py#L38
import ast
def _normalize_proposal(proposal: Any) -> str:
    if isinstance(proposal, str):
        try:
            tree = ast.parse(proposal)
            return ast.unparse(tree)  # Normaliza indentaciones y formato estático
        except Exception:
            pass
    return json.dumps(proposal, sort_keys=True, default=str)
```

### 2. Hashing Determinista (cortex_hash)
Cada propuesta normalizada genera un identificador criptográfico único usando SHA-256:
$$H_i = \text{SHA-256}(\text{normalize}(P_i))$$

### 3. Quórum de Consenso Ponderado
La base de decisión se calcula ponderando las propuestas según la reputación activa $R_k$ de cada agente emisor $k$. Sea $V_h$ la masa de votos acumulada por el hash de propuesta $h$:

$$V_h = \sum_{\{node_i \mid H_i = h\}} R_i$$

Consenso alcanzado si y solo si la propuesta ganadora con hash $h_{win}$ supera el umbral bizantino:

$$\frac{V_{h_{win}}}{\sum R_{node}} \ge \tau \quad (\tau = 0.67 \text{ por defecto})$$

Si se alcanza el consenso de forma anticipada antes de finalizar todos los subagentes, la ejecución interrumpe las tareas pendientes mediante `t.cancel()` para mitigar el consumo de red (Anergía cero).

---

## 🛠️ Interfaz de Línea de Comandos (CLI)

El asalto táctico de `LEGIØN-1` se invoca sobre el entorno C5-REAL desde la terminal:

```bash
# Navegar al directorio de persistencia
cd ~/30_CORTEX

# Ejecutar misión con formación restrictiva TESTUDO
python scripts/legion_strike.py \
  --mission "Auditar logs buscando llaves privadas expuestas en texto plano" \
  --formation TESTUDO \
  --tolerance 0.67

# Simulación en seco (C4-SIM)
python scripts/legion_strike.py \
  --mission "Refactorizar el motor de enrutamiento" \
  --formation BLITZ \
  --sim
```

---

> [!CAUTION]
> **Consumo Térmico Máximo:** Las formaciones masivas (HYDRA, TESTUDO, LEVIATHAN) orquestan llamadas concurrentes masivas que pueden agotar la cuota de la API o inducir límites de velocidad de red. Úselas exclusivamente para Singularidades P0 o cuando la perfección estructural de producción sea innegociable.

