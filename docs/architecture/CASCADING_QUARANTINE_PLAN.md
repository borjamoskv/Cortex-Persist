# Materialización del Axioma 2: Cascading Quarantine (Graph Orphan)

Siguiendo con la inyección del `CORTEX-NATIVE-AI-MANIFESTO`, procedemos a implementar la regla termodinámica de dependencias cognitivas:
> *"If the root assumption collapses, the entire dependent branch must instantaneously orphan by index reference in O(1)."*

Actualmente, si el `BeliefEngine` recibe un veredicto de `QUARANTINE` de la Corte Suprema, solo aísla la creencia en disputa. Sin embargo, si esa creencia era el cimiento (root assumption) de otras 50 creencias derivadas, la red neuronal se corrompe porque mantiene axiomas vivos que dependen de un pilar destruido.

## User Review Required

El mecanismo propuesto implementará **Cascading Quarantine**:
1. Cuando una creencia es aislada, buscaremos todas las creencias activas en el grafo cuyo campo `supported_by` incluya la ID de la creencia destruida.
2. Esas creencias serán automáticamente puestas en cuarentena con el estado `BeliefStatus.QUARANTINED` y el motivo `"Cascading Quarantine: Dependent root belief {id} was quarantined"`.
3. El proceso será **recursivo**, purgando topológicamente toda la rama corrupta.

¿Autorizas la inyección de la recursividad topológica (Cascading Quarantine) en el `belief_engine.py`?

## Proposed Changes

### [MODIFY] [belief_engine.py](file://~/30_CORTEX/cortex/extensions/hypervisor/belief_engine.py)
- **Modificación:** Introducir el método `_cascade_quarantine(self, root_id: str, reason: str)` que se disparará automáticamente al final de `_quarantine_belief`.
- **Mecanismo:** El motor buscará en la caché (y mediante llamadas al DB subyacente si la abstracción lo permite) cualquier creencia hija donde `root_id` esté presente en `supported_by`. Recursivamente aislará cada nodo encontrado.

## Verification Plan

### Automated Tests
- Simular la cuarentena de una creencia *padre* y verificar que las creencias *hijas* desaparecen del contexto activo (`_load_context`).
