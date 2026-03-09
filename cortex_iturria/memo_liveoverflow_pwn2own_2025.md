# CORTEX MEMO — LiveOverflow: Pwn2Own 2025 Berlin Documentary (Mozilla)

> **Source:** YouTube (LiveOverflow) · **4 partes** · **~71 min total**  
> **Fecha publicación:** 2026-02-22 · **Ingested:** 2026-03-09  
> **Contexto:** LiveOverflow documenta desde dentro cómo Mozilla responde a vulnerabilidades críticas descubiertas en Pwn2Own 2025 Berlin.

---

## SERIE COMPLETA

| Parte | Título | Duración | URL |
|:-----:|:-------|:--------:|:----|
| 1 | The World's Hardest Hacking Competition | 14:25 | [YouTube](https://youtu.be/YQEq5s4SRxY) |
| 2 | The First Exploit | 15:10 | [YouTube](https://youtu.be/uXW_1hepfT4) |
| 3 | Firefox JIT Bug | 20:14 | [YouTube](https://youtu.be/NT1VCmJF3mU) |
| 4 | Security-driven Rapid Release | 21:21 | [YouTube](https://youtu.be/x4CUAuwoZVk) |

---

## RESUMEN EJECUTIVO

Documental insider de Pwn2Own 2025 (Berlin). LiveOverflow obtuvo acceso exclusivo al **disclosure room** de Mozilla — la sala donde los equipos de seguridad reciben los detalles de los exploits inmediatamente después de la demostración exitosa.

### Temas Clave por Parte

**Part 1 — La Competición**
- Formato de Pwn2Own: hackers tienen tiempo limitado para explotar targets en vivo
- Sistema de disclosure: tras exploit exitoso, vendor recibe detalles inmediatos
- Mozilla como caso de estudio — equipo de seguridad de Firefox presente en Berlin
- Presión: vulnerabilidades en browsers = riesgo masivo para usuarios

**Part 2 — El Primer Exploit**
- Primer exploit exitoso contra Firefox en la competición
- Proceso de disclosure room: investigador explica el bug al equipo de Mozilla
- Cadena de exploit típica: bug de corrupción de memoria → escape de sandbox
- Reacción del equipo de seguridad ante vulnerabilidad zero-day en su producto

**Part 3 — Firefox JIT Bug**
- Vulnerabilidad en el **JIT compiler** de Firefox (SpiderMonkey)
- JIT bugs: el compilador Just-In-Time genera código máquina con asunciones incorrectas
- Tipo de bug: confusión de tipos (type confusion) o eliminación incorrecta de bounds checks
- Complejidad de auditar código generado dinámicamente

**Part 4 — Security-driven Rapid Release**
- Proceso de Mozilla para parchear vulnerabilidades Pwn2Own
- **Timeline:** Desde disclosure → análisis → patch → release para millones de usuarios
- Infraestructura de rapid release: cómo se publica un hotfix de seguridad en Firefox
- Balance: velocidad de parche vs riesgo de regresiones
- Blog post de referencia: [Firefox Security Response to Pwn2Own 2025](https://blog.mozilla.org/security/2025/05/17/firefox-security-response-to-pwn2own-2025/)

---

## CONCEPTOS TÉCNICOS CUBIERTOS

| Concepto | Descripción |
|:---------|:------------|
| **Pwn2Own** | Competición de hacking más prestigiosa. Investigadores explotan targets (browsers, VMs, coches, etc.) por premios en efectivo. Vendors presentes para disclosure inmediato |
| **Disclosure Room** | Sala privada donde investigador explica su exploit al vendor — acceso exclusivo documentado por primera vez |
| **JIT Compilation Bugs** | Vulnerabilidades en el compilador Just-In-Time de browsers — genera código nativo con asunciones que pueden ser violadas |
| **Type Confusion** | Bug donde el runtime trata un objeto como un tipo diferente, permitiendo acceso a memoria fuera de límites |
| **Rapid Security Release** | Pipeline de Mozilla para publicar patches de seguridad en horas/días post-disclosure |
| **Browser Exploit Chain** | Típicamente: memory corruption → arbitrary read/write → sandbox escape → code execution |

---

## RELEVANCIA PARA CORTEX

- **Modelo de respuesta a incidentes** aplicable a cualquier sistema
- **JIT bugs** relevantes para entender V8/SpiderMonkey (útil para Node.js security)
- **Disclosure process** como referencia para responsible disclosure
- Perspectiva insider única de cómo un vendor major maneja zero-days en producción

---

## NOTA

⚠️ Transcripciones completas no extraídas (YouTube IP rate limit tras extracciones masivas de la playlist Binary Exploitation). Los resúmenes están basados en metadata, descripción del autor, y títulos. Re-ingestar transcripciones en próxima sesión si necesario.

---

*CORTEX Memo — Pwn2Own 2025 Documentary · LiveOverflow · Ingested 2026-03-09*
