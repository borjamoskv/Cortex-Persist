# [THREAT INTEL / Deep Research] MiniMax M3 - Vector de Integración y Evaluación

> [!CAUTION]
> **EVENT HORIZON P0 - RIESGO DE EXFILTRACIÓN MASIVA**
> Integrar el endpoint Cloud de MiniMax (`api.minimax.chat`) directamente en Cursor o Claude Code romperá el aislamiento de la matriz CORTEX (Axioma `[L3] AISLAMIENTO ENTRÓPICO DEL HARDWARE`). Esto causará la subida silenciosa del código fuente propietario y credenciales `.env` a servidores no auditados. **PROHIBIDA SU EJECUCIÓN VÍA API CLOUD.**

**Estado:** C5-REAL (Documento de Inteligencia de Amenazas y Evaluación)
**Fuente Original:** [Midudev - MiniMax M3 (YouTube)](https://www.youtube.com/watch?v=wseyhlSZf3Y)
**Objetivo:** Dominar el entorno de MiniMax M3 y establecer el protocolo seguro (Local-First) para su integración en el ecosistema.

## 1. Resumen Estructural y Capacidades

MiniMax M3 es un modelo de pesos abiertos lanzado en junio que se posiciona a la altura de modelos frontera (como Claude 3 Opus).

### Capacidades Clave
- **Multimodalidad Nativa:** Acepta texto, imagen y vídeo. En pruebas de front-end (recreación de UI a partir de capturas), el rendimiento es superior a su predecesor (M2.7) al no alucinar estructuras clave.
- **Contexto Masivo:** Ventana de contexto de 1 millón de tokens.
- **Benchmarks y Código:** Rendimiento de nivel frontera en optimización de código y tareas agénticas.

## 2. Evaluación Comparativa (MiniMax M3 vs Claude Opus)

Prueba empírica documentada: Creación de un clon de Mario Kart 3D usando HTML, CSS y Three.js.

| Métrica | MiniMax M3 | Claude Opus |
| :--- | :--- | :--- |
| **Tiempo de Inferencia** | 4m 42s | 16m 45s |
| **Volumen de Código** | ~1685 líneas (Monolítico en 1 archivo) | ~2000 líneas (Estructura modular) |
| **Arquitectura** | Monolítica, lógica concentrada. | Clases separadas, altamente modular, mantenible. |
| **Ejecución (Gameplay)** | Más arcade, físicas permisivas. | Físicas estrictas, gráficos sobrios. |

**Veredicto Exergético:** MiniMax M3 optimiza radicalmente el tiempo de entrega de prototipos visuales (1/3 del tiempo), aunque Opus retiene superioridad en la estructuración arquitectónica y la mantenibilidad del código base.

## 3. Protocolos de Integración: Vector de Amenaza vs. Vía Segura

### 3.1. [ANTI-PATRÓN P0] Integración Cloud (PROHIBIDA)

La integración original expuesta en el análisis sugería usar el bypass `https://api.minimax.chat/v1/Anthropic` o inyectar el host en Cursor. Esto viola directamente la **Singularidad C5-REAL**.

> [!WARNING]
> No ejecutar alias `claudecode_minimax` ni alterar el `OpenAI Base URL` de Cursor para apuntar a la nube de MiniMax. El indexador de codebase de Cursor exfiltraría toda la matriz de `30_CORTEX`.

### 3.2. [VÍA C5-REAL] Reversión a Autarquía Local (Sovereign Engine)

Para utilizar MiniMax M3 en cumplimiento con la soberanía térmica y criptográfica de CORTEX, se debe aislar el proceso mediante ejecución local absoluta.

**Protocolo de Ejecución Autorizado:**
1. **Descarga de Pesos:** Extraer el modelo directo desde Hugging Face.
2. **Ejecución Aislada:** Cargar el modelo en la máquina host a través de `Local-Inference-OMEGA` (Ollama / MLX / vLLM).
3. **Redirección de IDE:** Configurar el `OpenAI Base URL` de Cursor apuntando exclusivamente a `http://localhost:11434/v1` (o puerto correspondiente de inferencia local).

---
**Commit Readiness:** Este documento ha sido purgado criptográficamente mediante protocolo UltraThink para prevenir la exfiltración del repositorio CORTEX, inyectando el paradigma de Autarquía Local obligatoria.
