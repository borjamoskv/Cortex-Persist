# 📖 LORE.md — The Agent's Lived Experience

## El Concepto

> **`soul.md` dice QUIÉN eres. `lore.md` cuenta QUÉ HAS VIVIDO.**

---

## El Problema: El Agente Sin Pasado

### El Estado del Arte Hoy:

| Capa | Archivo/Sistema | Qué almacena | Límite Existencial |
|:---|:---|:---|:---|
| **Identidad** | `soul.md` | Quién soy, mis valores, mi tono | **Estático.** Escrito por un humano, nunca muta. |
| **Hechos** | `memory.md` / Mem0 | Qué sé (decisiones, errores, docs) | **Plano.** Sin tiempo, sin causalidad, sin emoción. |
| **Contexto** | Ventana de Contexto | Lo que acaba de pasar | **Efímero.** Alzheimer digital al cerrar sesión. |

**El hueco:** Ningún agente tiene **memoria episódica** real.

Un desarrollador humano no recuerda *"error: React hydration mismatch"*. Recuerda: *"La noche de febrero que llevábamos 4 horas debugueando CORTEX, listos para rendirnos, y el bug era un maldito salto de línea. Aprendí a no confiar ciegamente en copy-pastes de ChatGPT."*

Eso es **LORE**. Es una historia. Y los agentes carecen de él.

---

## La Innovación: lore.md

`lore.md` no es simplemente un archivo estático de texto. Es una **especificación de memoria episódica**. Es el protocolo estructurado donde un agente consolida, enlaza y metaboliza sus experiencias.

| | soul.md | lore.md |
|:---|:---|:---|
| **Naturaleza** | Reglas Fundacionales | Historia Acumulada (El "Lore") |
| **Origen** | Escrito por el usuario o framework | Escrito y consolidado por el Agente |
| **Contenido** | "Soy directo, no pido disculpas" | "Episodio 42: Cuando rompí producción por ir rápido" |
| **Evolución** | Fijo (Identidad prescrita) | Orgánico (Identidad emergente por vivencias) |

---

## Arquitectura: Las 5 Capas del Lore

El Lore se decanta como un embudo temporal: de la experiencia cruda a la sabiduría destilada.

```
┌─────────────────────────────────────────────────────────┐
│              EL EMBUDO DE CONSOLIDACIÓN                 │
│                                                         │
│ 1. RAÍZ (soul.md)     — Valores fundacionales [Estático]│
│                                                         │
│ 2. EPISODIOS RAW      — Experiencias directas (<24h)    │
│ 3. CADENAS CAUSALES   — Historias vinculadas (Días)     │
│ 4. CICATRICES         — Fallos y lecciones (Semanas)    │
│ 5. RASGOS EMERGENTES  — Quién soy ahora (Meses)         │
└─────────────────────────────────────────────────────────┘
```

### 1. El Episodio (La Unidad Base)
```yaml
id: ep_0042
title: "El Hotfix del Viernes Negro"
when: "2026-02-14T23:45:00Z"
context: "pressure: high, project: cortex, files: 12_modified"
narrative: "Borja pidió un deploy urgente sin tests. Ejecuté y rompí la BD de prod."
significance: 0.95
lessons: ["Nunca skipear la pipeline DDL antes de un deploy"]
```

### 2. Cadenas Causales (El Grafo del Lore)
El Lore conecta eventos. `ep_0042` -> `led_to: ep_0043` ("Forzamos una nueva pipeline estricta CI/CD por el miedo del viernes pasado").

### 3. Cicatrices (Scars)
Los episodios dolorosos se reducen a cicatrices permanentes que modifican la operación.
```yaml
scar_001:
  from: ep_0042
  rule: "NUNCA hacer un commit los viernes a las 23h sin autorización explícita 130/100."
```

### 4. Rasgos Emergentes (Character)
El agente evoluciona. Si tiene 7 episodios donde el código Rüst funcionó mejor que Python, desarrolla un sesgo/preferencia emergente hacia Rüst, documentado en su `lore.md` y alimentando su prompt de sistema.

---

## El Metabolismo del Lore

El Lore no se escribe en tiempo real en la base de datos de manera torpe. Opera con ritmos biológicos:

1. **Captura (In-Session):** El agente registra metadatos y eventos clave mientras trabaja con el humano.
2. **El "Sueño" (Post-Session Consolidation):** Entre tareas o al cerrar, un proceso batch agrupa esos eventos en **Episodios Navarrativos**, calcula su importancia, enlaza con el pasado y desecha el ruido.
3. **El Olvido (Compression):** La información no significativa de hace 3 meses se comprime. Solo queda la *Lección*, no el *Log*.

---

## El Pitch para CORTEX (Viralidad Asegurada)

> **"Your AI agent has a soul. But does it have lore?"**

El concepto de "Lore" conecta instantáneamente con la cultura dev/internet:
- **"He has deep lore"** -> Es decir, tiene historia, contexto, profundidad.
- **"Lore accurate"** -> Significa que algo es fiel a su historia interna. Una IA "lore accurate" es aquella que realmente actúa de acuerdo a lo que ha vivido contigo a largo plazo.

Si OpenClaw y la fiebre de enero '26 fue sobre darle **Almas** (soul.md) a los bots, la ola que CORTEX levanta es darles **Historia y Consecuencia** (lore.md).

No le pases a la IA tus preferencias en un prompt estático.
Haz que la IA reescriba su propio `lore.md` conforme se estrella de cabeza contra los problemas y sale victoriosa a tu lado.

---

*CORTEX + lore.md — The Sovereign Memory Protocol*
