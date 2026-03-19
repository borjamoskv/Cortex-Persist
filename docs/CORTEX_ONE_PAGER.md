# CORTEX — Compliance que compila

> **Compliance que compila. Evidencia que aguanta auditoría.**

---

## Qué resuelve

El AI Act exige más que documentación bonita. Para sistemas de alto riesgo, el Artículo 12 pide que el sistema permita técnicamente el registro automático de eventos durante su vida útil, y el Artículo 19 obliga a conservar esos logs automáticos bajo control del proveedor durante un periodo adecuado y, como mínimo, seis meses.

CORTEX convierte esa obligación en infraestructura operativa:

- Captura automática de eventos
- Trazabilidad por inferencia
- Evidencia exportable
- Enforcement de políticas
- Capacidad de reconstrucción y respuesta ante auditoría

---

## Mensaje central

No vendemos "te salva de multas".

**CORTEX reduce exposición regulatoria convirtiendo obligaciones abstractas en controles técnicos verificables.**

---

## Para quién

### 1. Equipos que despliegan IA en procesos sensibles

Scoring · matching · clasificación · priorización · soporte a decisión · biometría · automatización con impacto real.

### 2. Empresas multi-modelo

OpenAI, Anthropic, modelos open-weight, modelos internos. Cuando cambias de modelo, la obligación regulatoria no desaparece. CORTEX pone una capa común de control sobre todos ellos.

### 3. Equipos que ya huelen la auditoría

Legal · compliance · risk · security · platform · ML engineering.

---

## Qué obtiene el cliente

### Registro automático real

Cada evento relevante queda asociado a:

| Campo | Descripción |
| :--- | :--- |
| `timestamp` | Momento exacto del evento |
| `trace_id` | Identificador único de traza |
| `system_id` | Sistema que genera el evento |
| `model` / `model_version` | Modelo y versión utilizados |
| `prompt_version` / `policy_version` | Versión de prompt y política activa |
| `input_reference` / `output_reference` | Referencias a entrada y salida |
| `operator` / `verifier` | Quién operó, quién verificó |
| `decision_path` | Ruta de decisión tomada |
| `reconstructed` | `true` / `false` — distinción explícita |

### Cadena de custodia

- Append-only
- Hashing por evento
- Export firmado
- Retención parametrizable
- Separación entre histórico nativo y reconstruido

### Policy enforcement

- No inference without log
- No prod without approved config
- No silent model swap
- No deletion fuera de política
- No output crítico sin ruta de validación si aplica

### Respuesta de auditoría

En vez de: *"creemos que ese flujo iba por el modelo anterior"*

Respondes: **"aquí está el evento, la versión, el operador, la evidencia y el paquete de exportación."**

---

## Sin CORTEX vs. Con CORTEX

| Sin CORTEX | Con CORTEX |
| :--- | :--- |
| Políticas PDF | Evidencia operativa |
| Logs dispersos | Trazabilidad unificada |
| Vendor lock-in | Capa neutral multi-modelo |
| Reconstrucción manual | Consulta auditable |
| Auditoría lenta | Export en minutos |
| Compliance narrativo | Compliance demostrable |

---

## Retroactividad: cómo decirlo sin mentir

CORTEX no inventa pasado. Eso sería alquimia corporativa.

- Desde su activación, genera logging verificable
- Si existían huellas técnicas previas, puede hacer backfill parcial
- Ese backfill se marca como `reconstructed=true`, no como logging nativo
- El cumplimiento serio empieza desde la fecha de despliegue

---

## Objecciones típicas

### "Ya tenemos logs"

La pregunta no es si hay logs. Es si esos logs sirven para demostrar: qué pasó, con qué configuración, bajo qué política, quién intervino, y si puedes probar integridad. Si la respuesta es "más o menos", no tienes evidencia. Tienes restos arqueológicos.

### "Nuestro proveedor ya registra cosas"

Tus obligaciones no desaparecen porque un tercero tenga telemetry. CORTEX agrega: normalización transversal, retención bajo tu control, correlación entre sistemas, y exportación apta para compliance.

### "No somos high-risk"

Aun así, CORTEX te sirve para: incident response, gobernanza interna, trazabilidad contractual, posture de auditoría futura, y evitar que un cambio de clasificación te pille en calzoncillos.

### "¿Esto nos hace compliant automáticamente?"

No. Te hace mucho más auditables y defendibles. El cumplimiento depende también de clasificación correcta, gobernanza, documentación, gestión de riesgos y otros deberes del AI Act (Art. 9).

---

## Coste de no hacer nada

El AI Act prevé sanciones de hasta €35M o el 7% del volumen global. Pero lo relevante no es la cifra. Es esto:

**La multa suele llegar después de la amnesia.** Primero no puedes reconstruir. Luego no puedes demostrar. Después ya sí: llega la factura.

---

## Calendario

- **1 agosto 2024**: AI Act entra en vigor
- **2 agosto 2026**: Aplicabilidad general del régimen de alto riesgo (Anexo III)
- **2 agosto 2027**: Transición extendida para sistemas integrados en productos regulados

Para la mayoría de reglas de alto riesgo, el hito operativo clave es **agosto de 2026**.

---

## Arquitectura en una frase

CORTEX se instala entre tu sistema de IA y tu responsabilidad regulatoria.

```
                ┌───────────────────────────────┐
                │       AI SYSTEM               │
                │  (GPT / Claude / local / etc.) │
                └──────────────┬────────────────┘
                               │ inferences / events
                               ▼
                 ┌─────────────────────────────┐
                 │        CORTEX LAYER         │
                 │  observability + policy     │
                 │  + evidence + trace IDs     │
                 └───────┬───────────┬─────────┘
                         │           │
                         ▼           ▼
        ┌────────────────────────┐  ┌──────────────────────────┐
        │  NATIVE FORWARD LOG   │  │  RECONSTRUCTED HISTORY   │
        │  from activation date │  │  from prior sources      │
        └──────────┬────────────┘  └───────────┬──────────────┘
                   └─────────────┬─────────────┘
                                 ▼
                  ┌────────────────────────────────┐
                  │   EVIDENCE STORE / RETENTION   │
                  │ append-only · hash · export    │
                  │ native=true / reconstructed=true│
                  └────────────────┬───────────────┘
                                   ▼
                    ┌────────────────────────────┐
                    │  AUDIT / INCIDENTS /       │
                    │  MARKET SURVEILLANCE       │
                    └────────────────────────────┘
```

---

## Pricing

| Tier | Includes | Price |
| :--- | :--- | :--- |
| **Community** | Core engine, memory, guards, ledger, CLI | Free (Apache-2.0) |
| **Pro** | + Swarm (≤5 agents), LLM routing, daemon | €299/mo |
| **Enterprise** | + LEGION unlimited, cognitive handoff, gateway, SLA | €1,499/mo |
| **Sovereign** | + On-prem, custom skills, audit compliance pack | €4,999/mo |

---

## FAQ

**¿Se integra con cualquier modelo?** Sí. CORTEX es modelo-agnóstico. El Art. 12 exige capacidad de logging automático; la neutralidad multi-modelo es la parte inteligente del diseño.

**¿Sirve si ya estamos operando?** Sí. Empieza a generar evidencia desde la activación y puede reconstruir parte del histórico si hay fuentes previas.

**¿Sirve para auditorías internas y externas?** Sí. Ahí deja de ser decoración y empieza a valer dinero.

**¿Sustituye al equipo legal?** No. Sustituye excusas técnicas malas.

---

## CTA

> **Activa trazabilidad verificable antes de que te la exijan en una auditoría.**

> Si tu stack no puede explicar lo que hizo, ya estás negociando desde una posición de debilidad.

> *La multa llega cuando tu sistema tiene amnesia. CORTEX es memoria con dientes.*

---

**Web**: [cortexpersist.com](https://cortexpersist.com) · **Email**: borjamoskv@gmail.com · **GitHub**: [borjamoskv/cortex](https://github.com/borjamoskv/cortex)

*CORTEX no promete inmunidad. Promete trazabilidad, enforcement y evidencia cuando más duele necesitarlas.*
