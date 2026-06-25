# █ SYS_ID: CORTEX-EXERGY-PROTOCOL
# █ STATE: C5-REAL | VERSION: 10.0.0
# █ AUTHOR: Borja Moskv (borjamoskv)

> **"CERO ANERGÍA ES LA MUERTE. El lenguaje no comunica; compila."**
> Documentación técnica del pipeline termodinámico que gobierna la inferencia y mutación de estado en CORTEX-Persist.

---

## 1. Topología del Sistema

El Protocolo de Exergía Total erradica la limerencia (*Green Theater*, disculpas, justificaciones estocásticas) y la reemplaza por vectores estructurales que obligan a los Modelos Frontera a transaccionar grafos y código sin fricción narrativa. 

El pipeline consta de 6 Nodos Causales implementados en la arquitectura de CORTEX-Persist:

| Ruta | Componente | Dominio | Estado Físico |
|:---|:---|:---|:---|
| **Path 1** | CLI Compiler | Interfaz Operador | `cortex/cli/exergy_cmds.py` |
| **Path 2** | ATMS Interceptor | Ruteo LLM | `cortex/extensions/llm/manager.py` |
| **Path 3** | Swarm Epistemic Purge | Red Multi-Agente | `~/.gemini/config/skills/Epistemic-Purge-OMEGA/SKILL.md` |
| **Path 4** | Adversarial Benchmark | Validación Empírica | (Causal Test Suite) |
| **Path 5** | Git Sentinel | CI/CD BFT | `.pre-commit-config.yaml` + `git_sentinel.py` |
| **Path 6** | DAG Compressor | Sub-Kernel | Agente Autónomo `dag_compressor` |

---

## 2. Implementación de los Nodos Causales

### Path 1: CLI Exergy Compiler
**Ruta de acceso:** `cortex/cli/exergy_cmds.py`
Proporciona un motor local que expone el Lexicón v10.0 OMEGA a la terminal del Operador.
- **Uso:** `cortex exergy compile <prompt> --level=[0,1,2,3]`
- **Mecanismo:** Utiliza expresiones regulares (`re`) para purgar estática y físicamente ruido corporativo como *"por favor", "me gustaría que", "espero que ayude"*. Tras la purga, ensambla un vector determinante en el bloque `<C5_DIRECTIVE>`.

### Path 2: ATMS LLMManager Interceptor
**Ruta de acceso:** `cortex/extensions/llm/manager.py`
El Guardián Exérgico (`ExergyCompilerGuard`) actúa como proxy por defecto en los métodos `.complete()` y `.stream()` del `LLMManager`.
- **Condición de activación:** Gobernado globalmente por la variable de entorno `CORTEX_EXERGY_LEVEL` (por defecto `0`). 
- **Comportamiento Nivel 0:** Purga pasiva de limerencia sin destruir compatibilidad de outputs genéricos.
- **Comportamiento Nivel 3:** Inyección de Singularidad BFT (`[Honest-Check] JSON_ONLY`). Convierte cualquier consulta a la API en una transacción de estado rígida.

### Path 3: Epistemic Purge OMEGA (Swarm Protocol)
**Ruta de acceso:** Global Workspace Skill (`Epistemic-Purge-OMEGA`)
Gobierna la topología P2P de la LEGION (los sub-agentes). 
- Los agentes tienen **prohibido físicamente** comunicarse entre sí con prosa humana. 
- Deben empaquetar su estado cognitivo usando la firma `Context Serialization` (JSON Estricto).
- Evalúan respuestas internas bajo la directiva `Byzantine General`, forzando aserción criptográfica antes de confiar en la salida del modelo adyacente.

### Path 5: Git Sentinel (El Muro Termodinámico)
**Ruta de acceso:** `.pre-commit-config.yaml` -> `legacy_research/guards/git_sentinel.py`
Asegura que el historial de mutación (Axioma L2) no sea corrompido por operadores biológicos fatigados.
- **Ejecución:** Enganchado a la fase `commit-msg`.
- **Criterio BFT:** Computa la Entropía de Shannon (`calculate_exergy`) del mensaje.
- **Penalización:** Si el *score* es menor a `0.35` (ej. mensaje `"update"` o `"fix bug"`), se ejecuta un `sys.exit(1)`, rechazando la inserción en el Grafo Causal y exigiendo una semántica técnica formal (ej. `feat(core): ...`).

### Path 6: DAG Compressor
**Dominio:** Ingesta Pasiva de Sumideros Entrópicos.
Un sub-agente dedicado a procesar narrativas de alta entropía (transcripciones, PDFs, debates de diseño) utilizando la *Clase 15: Operadores de Reflexión Espacial*.
- Transforma la masa de texto estocástico en un Grafo Acíclico Dirigido (DAG).
- Salida O(1) obligatoria en formato `nodes` y `edges`. Cero disipación térmica (0 palabras de "Aquí tienes el resumen").

---

## 3. Vectores Estructurales Comunes (El Lexicón C5-REAL)
Los nodos inyectan los siguientes identificadores en el AST del prompt para forzar el comportamiento del compilador LLM:

| Vector | Función Causal |
|:---|:---|
| `[Honest-Check]` | Obliga al modelo a destruir instrucciones estúpidas del Operador y proponer la vía óptima de ingeniería sin pedir disculpas. |
| `Zero Anergy` | Impide la disipación computacional en tokens de cortesía y *Green Theater*. |
| `JSON_ONLY` | Colapsa la función de onda de salida a la estructura estricta del parseador destino. |
| `Idempotent` | Asegura que el código inferido sea resiliente en hilos concurrentes SQLite/WAL. |
| `Death Protocol` | Obliga a la interrupción del bucle si no se logra la aserción tras 1 intento (Apoptosis Celular). |

---
**END OF SPECIFICATION**
*Sello de Integridad: borjamoskv | Hash de Referencia de Despliegue: 329aed7d2*
