# RFC — CORTEX Immunity Layer v0.1

> De memoria verificada a inmunidad computacional

## 1. Propósito

CORTEX no debe limitarse a persistir estado con trazabilidad.
Debe detectar, contener, degradar, amputar y auditar estado con potencial de replicación entrópica.

La capa de inmunidad define cómo el sistema clasifica y gobierna artefactos, bloques, ramas y memorias cuando existe riesgo de contaminación causal.

---

## 2. Axiomas

**AX-IMM-01 — Promoción inmunológica**
Ningún estado con capacidad de propagación causal puede ser promovido sin perfil inmunológico explícito.

**AX-IMM-02 — Seal como frontera soberana**
Toda mutación sobre estado sellado se interpreta primero como incidente de seguridad, no como error de aplicación.

**AX-IMM-03 — Error replicante**
Un error deja de ser bug local cuando puede alterar memoria, routing, planeación, consenso o ejecución downstream.

**AX-IMM-04 — Amputación > contaminación**
Ante incertidumbre semántica con potencial de replicación, el sistema debe preferir pérdida local de trabajo frente a degradación topológica global.

**AX-IMM-05 — Novedad ≠ infección**
Rareza, exploración o divergencia no constituyen patología por sí mismas. La inmunidad debe penalizar replicación riesgosa, no creatividad.

---

## 3. Ontología operativa

- **Guard**: Control de admisión. Decide si algo entra.
- **Seal**: Control de irreversibilidad. Decide qué queda fuera del universo mutable.
- **Pathogen**: Artefacto o mutación con potencial de replicación causal entrópica.
- **Necrosis semántica**: Estado no necesariamente falso, pero demasiado degradado para permanecer conectado al canon operativo.
- **Quarantine**: Estado intermedio entre observación y promoción. Sirve para impedir sellado prematuro.
- **Amputation**: Desacoplamiento irreversible de una rama, bloque o flujo comprometido.

---

## 4. Tipos mínimos & Máquina de Estados

La capa de inmunidad provee tipos estructurales rigurosos integrados en `cortex.immunity`.

### Transiciones Válidas

- `observed`     -> `quarantined`, `promotable`
- `quarantined`  -> `promotable`, `necrotic`
- `promotable`   -> `sealed`, `quarantined`
- `sealed`       -> `necrotic`      *(solo por evidencia forense)*
- `necrotic`     -> `amputated`

**Reglas**
- `observed`: artefacto recién ingresado; no confiable todavía.
- `quarantined`: congelado para análisis; no puede propagarse.
- `promotable`: supera umbral de admisión y tiene trazabilidad suficiente.
- `sealed`: canonizado; mutación prohibida.
- `necrotic`: detectada degradación incompatible con continuidad.
- `amputated`: aislado del DAG causal y excluido de promoción futura.

---

## 5. Pipeline canónico

```text
ingestión
  → guards
    → scoring patógeno
      → quarantine decision
        → verificación cruzada
          → promoción
            → seal
              → auditoría post-seal
                → vigilancia de necrosis tardía
```

---

## 6. Distinción formal: Guard vs Seal

**Guard falla** → rechazo o cuarentena.  (Manejado como excepción validación de admisión)
**Seal falla** → incidente de seguridad. (El hash inmutable criptográfico detectó mutación tras haberse sellado la memoria)

Regla dura para Seals:
- un `SealRecord` no se edita.
- si cambia el contenido, cambia el objeto.
- si un contenido sellado parece mutar, no se "corrige": se abre incidente.

---

## 7. Necrosis semántica

No hace falta demostrar falsedad absoluta. Basta con umbrales operativos.

**Señales de necrosis:**
- Contradicción incremental > 70%
- Pérdida de provenance < 30%
- Dependencia de entradas ya marcadas como necróticas > 20%
- Reescrituras repetidas >= 4 veces
- Divergencia contra estado sellado
- Incremento de fan-out causal desde una fuente dudosa

---

## 8. Modos operativos

**Exploration Mode**
Para I+D, ideación, creatividad, búsqueda.
- guards laxos, más cuarentena, seals tardíos.
- tolerancia alta a rareza, promoción reversible o provisional.

**Critical Mode**
Para memoria central, consenso, ledger, ejecución autónoma.
- guards estrictos, scoring agresivo, seals tempranos.
- amputación inmediata ante contradicción severa.
- reuse solo desde estado promotable/sealed.

---

## 9. Riesgo de autoanticuerpos

El sistema inmune puede degenerar en burocracia con esteroides. 
*Síntomas:* todo lo raro cae en cuarentena, nada llega a seal, branches exploratorias se tratan como incidentes.

**Mitigación:** Separar novedad de replicación riesgosa, no aplicar política de producción a zonas creativas, medir falsos positivos inmunes.
Métrica útil: `immune_false_positive_rate = artefactos útiles retenidos / artefactos útiles evaluados`

---

## Invariante Principal
La versión que fija todo el documento fundacional:
**"CORTEX no trata el error como una anomalía local, sino como materia entrópica con potencial de replicación causal. Por ello, todo estado relevante atraviesa admisión, perfil inmunológico, cuarentena, promoción y sellado antes de integrarse en la continuidad cognitiva."**
