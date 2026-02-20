# ⚔️ BATTLE PLAN: CORTEX-L2/L3 (OUROBOROS-∞)

> **"Adversarial First. Cada mejora se gana en el fuego."**

## 1. OBJETIVOS PRINCIPALES
- **Erradicar Dependencias Ambientales**: Aislar `test_cdc.py` y resolver `neo4j.exceptions.ServiceUnavailable` mediante inyección de dependencias `Mock` o decorators condicionales de integración en la pipeline de tests.
- **Resolver Entropía Acumulada**: Cerrar procesos MCP huérfanos y reconducir consumo del daemon CLI de CORTEX que está generando colisiones locales.
- **Persistencia**: Registrar meta-aprendizaje en CORTEX post-sesión.

## 2. EJECUCIÓN: ENJAMBRE ADAPTATIVO

### OLA 1: Contención de Caos & Fuga (L0)
- Identificar procesos `python -m cortex.mcp` sin padre.
- Matarlos ordenadamente (Graceful shutdown o SIGKILL si derivan).
- **Red Team Attack**: "¿No tirará eso el servidor en vivo o a otros clientes del usuario?"
- **Resolución**: Comprobar primero parent process. Si es init(1), se asumen huérfanos perdidos y se fulminan.

### OLA 2: Reparación de Tests Causal (L1)
- **Operación**: Aislar Neo4j.
- Inspeccionar `tests/test_cdc.py` y `test_cdc_outbox_flow`.
- Identificar por qué Neo4j trata de conectarse en entorno local no-aislado.
- Añadir `@pytest.mark.integration` o un mock `neo4j.GraphDatabase.driver` explícito usando `unittest.mock`.

### OLA 3: Mejora Sistémica (L4)
- **Acción Ouroboros**: Comprobar si hay otros tests intentando pegarle a Redis, PostgreSQL u otras DB.
- **CORTEX Persistencia**: Registrar que los componentes de persistencia en local lanzan excepción de Socket 61 en lugar de Mockear por defecto.

## 3. CHECKPOINTS DE CAOS
- [x] Comprensión del Entorno y Lectura de Entropía
- [ ] OLA 1 - Limpieza de Daemon MCP.
- [ ] OLA 2 - Fijar `test_cdc.py` para aislarlo
- [ ] Reejecución Paralela de `pytest` (Verificación de Victoria)
- [ ] Metareflexión -> Guardar Patrón Causal en CORTEX.
