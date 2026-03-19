# Protocolo de Aceptación Técnica y Funcional — CORTEX

**Documento:** UAT/SAT CORTEX
**Versión:** 1.0
**Objetivo:** Validar que CORTEX cumple los requisitos funcionales, operativos y probatorios necesarios para soportar trazabilidad, enforcement y auditoría en flujos de IA.
**Entorno:** Staging / Preproducción / Producción controlada
**Fecha:** [YYYY-MM-DD]
**Responsable cliente:** [Nombre]
**Responsable técnico:** [Nombre]

---

## 1. Tabla de Validación Comercial

| Área | Qué prometemos | Cómo se valida | Evidencia aceptable | Criterio de aceptación |
| :--- | :--- | :--- | :--- | :--- |
| **Captura automática** | CORTEX registra automáticamente los eventos relevantes del sistema de IA | Ejecutar batería de inferencias controladas y comparar eventos emitidos vs capturados | Reporte de ejecución, export JSON/CSV, conteo reconciliado | `capture_rate >= 99.8%` |
| **Trazabilidad** | Cada evento queda correlacionado con modelo, versión, input, output y operador | Consultar trazas por trace_id, modelo, ventana temporal y actor | Muestra de logs completos y consultas reproducibles | 100% de eventos de prueba localizables |
| **Integridad** | Los logs no pueden alterarse sin dejar rastro | Modificar artificialmente un evento en entorno de prueba y revalidar cadena | Verificación fallida de hash/cadena, alerta de tamper | 100% de alteraciones detectadas |
| **Enforcement** | Las políticas bloquean o marcan usos no conformes | Simular violaciones: modelo no aprobado, falta de metadata, logging caído, bypass de revisión | Alertas, bloqueos, eventos policy-driven | 100% de políticas críticas disparan respuesta esperada |
| **Auditoría** | Un auditor puede reconstruir un evento sin excavación manual | Simular solicitud de auditoría con rango temporal, sistema y evento concreto | Export firmado, consulta documentada, tiempos de respuesta | búsqueda <30s, export <2m |
| **Histórico** | CORTEX distingue entre evidencia nativa y reconstruida | Importar histórico previo y verificar etiquetado `reconstructed=true` | Registros separados, informe de importación | 0 mezcla entre nativo y reconstruido |
| **Multi-modelo** | La capa de control funciona con distintos modelos | Repetir mismo caso de prueba sobre 2+ backends | Reporte comparativo por backend | Misma estructura de trazabilidad en todos |
| **Defensa regulatoria** | CORTEX mejora posición probatoria ante auditoría | Ejecutar drill de evidencia end-to-end | Dossier de prueba, snapshots, logs, hashes | Evidencia suficiente para reconstruir caso completo |

---

## 2. Alcance

Este protocolo valida los siguientes dominios:

1. Captura automática de eventos
2. Trazabilidad y correlación
3. Integridad y detección de manipulación
4. Enforcement de políticas
5. Consulta y export para auditoría
6. Gestión de histórico reconstruido
7. Compatibilidad multi-modelo
8. Rendimiento operativo básico

---

## 3. Requisitos Previos

- CORTEX desplegado en entorno objetivo
- Logging habilitado
- Acceso a sistema de IA de prueba
- Dataset sintético preparado
- Políticas mínimas cargadas
- Mecanismo de export disponible
- Almacenamiento de evidencia habilitado
- Reloj de sistema sincronizado
- Usuarios de prueba definidos: `operator_test`, `reviewer_test`, `auditor_test`

---

## 4. Dataset de Prueba

Conjunto controlado con al menos estos casos:

- Caso nominal
- Input inválido
- Timeout
- Retry
- Modelo no aprobado
- Cambio de versión
- Revisión humana requerida
- Evento histórico importado

**Volumen mínimo recomendado:**
- 100 eventos para validación básica
- 1.000 eventos para stress ligero

---

## 5. Casos de Prueba

### CP-01 — Captura automática de eventos

**Objetivo:** Validar que CORTEX registra automáticamente todos los eventos relevantes.

**Procedimiento:**
1. Ejecutar 100 inferencias sintéticas
2. Registrar número exacto de eventos emitidos por sistema fuente
3. Consultar CORTEX y contar eventos capturados
4. Comparar ambos conjuntos

**Datos esperados por evento:**
`timestamp` · `trace_id` · `system_id` · `model` · `model_version` · `policy_version` · `input_ref` · `output_ref` · `status` · `native=true`

**Criterio de aceptación:**
- `capture_rate >= 99.8%`
- `orphan_log_rate <= 0.1%`
- 0 duplicados no justificados

**Evidencia:** reporte de ejecución, export de logs, reconciliación fuente vs CORTEX

---

### CP-02 — Trazabilidad por correlación

**Objetivo:** Validar que cada evento puede ser trazado de forma unívoca.

**Procedimiento:**
1. Seleccionar 10 eventos de prueba
2. Consultar por `trace_id`
3. Consultar por rango temporal
4. Consultar por modelo y actor
5. Verificar correlación input → output → revisión

**Criterio de aceptación:**
- 100% de eventos consultables
- Correlación completa en todos los casos muestreados

**Evidencia:** capturas/export de consultas, reporte de correlación

---

### CP-03 — Integridad / detección de manipulación

**Objetivo:** Validar que una modificación posterior de logs es detectable.

**Procedimiento:**
1. Generar lote de 100 eventos
2. Ejecutar snapshot/hash de integridad
3. Alterar manualmente 1 evento en entorno controlado
4. Reejecutar verificación

**Criterio de aceptación:**
- 100% de alteraciones detectadas
- Evento alterado marcado como inconsistente
- Cadena posterior invalidada o señalada según diseño

**Evidencia:** snapshot previo, snapshot posterior, reporte de verificación, alerta de tamper

---

### CP-04 — Enforcement de políticas críticas

**Objetivo:** Validar que CORTEX bloquea o marca comportamientos fuera de policy.

**Escenarios mínimos:**
- Inferencia sin logging activo
- Modelo no aprobado
- Falta de metadata obligatoria
- Output crítico sin reviewer
- Borrado fuera de retención

**Procedimiento:**
1. Ejecutar cada escenario
2. Registrar respuesta del sistema
3. Verificar generación de evidencia del evento de policy

**Criterio de aceptación:**
- 100% de escenarios críticos generan bloqueo o marcaje esperado
- Severidad correcta
- Evidencia persistida

**Evidencia:** logs de policy, alertas, capturas de respuesta del sistema

---

### CP-05 — Consulta para auditoría

**Objetivo:** Validar que un tercero puede reconstruir rápidamente un caso.

**Procedimiento:**
1. Simular solicitud: sistema X, fecha/hora específica, modelo Y, operador Z
2. Ejecutar consulta
3. Exportar resultado
4. Verificar integridad del paquete exportado

**Criterio de aceptación:**
- Consulta < 30 segundos
- Export < 2 minutos
- Paquete verificable
- 100% de campos necesarios presentes

**Evidencia:** query ejecutada, export CSV/JSON, prueba de integridad, tiempos medidos

---

### CP-06 — Histórico reconstruido

**Objetivo:** Validar la correcta separación entre evidencia originaria y reconstruida.

**Procedimiento:**
1. Importar lote histórico desde fuente previa
2. Verificar etiquetado `reconstructed=true`
3. Ejecutar consultas mixtas con eventos nativos y reconstruidos
4. Confirmar separación lógica y visual

**Criterio de aceptación:**
- 100% de eventos importados marcados como reconstruidos
- 0 eventos nativos mal etiquetados
- Consultas distinguen ambos tipos sin ambigüedad

**Evidencia:** informe de importación, muestra de eventos, capturas/export de consultas

---

### CP-07 — Compatibilidad multi-modelo

**Objetivo:** Validar que la estructura de evidencia se mantiene estable entre backends.

**Procedimiento:**
1. Ejecutar mismo set de 20 casos sobre backend A, B, C
2. Comparar estructura de logs
3. Verificar trazabilidad homogénea

**Criterio de aceptación:**
- Esquema consistente entre backends
- 100% de casos con campos mínimos obligatorios

**Evidencia:** export comparativo, diff de esquemas, reporte técnico

---

### CP-08 — Rendimiento operativo básico

**Objetivo:** Validar que la capa de evidencia no introduce degradación inaceptable.

**Métricas:**
- Latencia adicional por evento
- Tiempo de consulta p95
- Tiempo de export
- Tasa de error

**Criterio de aceptación:**
- Overhead por evento dentro del umbral acordado
- `audit_query_latency_p95 < 30s`
- `export_success_rate >= 99.9%`

**Evidencia:** benchmark, métricas p50/p95/p99, reporte de errores

---

## 6. KPIs de Aceptación

| KPI | Umbral |
| :--- | :--- |
| `capture_rate` | ≥ 99.8% |
| `orphan_log_rate` | ≤ 0.1% |
| `tamper_detection_rate` | = 100% |
| `policy_critical_detection_rate` | = 100% |
| `export_success_rate` | ≥ 99.9% |
| `audit_query_latency_p95` | < 30s |
| `historical_labeling_accuracy` | = 100% |

---

## 7. Evidencia Obligatoria a Conservar

- Plan de pruebas ejecutado
- Dataset sintético usado
- Configuración del entorno
- Versión exacta de CORTEX
- Resultados de cada caso de prueba
- Exports JSON/CSV
- Snapshots de integridad
- Logs de policy
- Métricas de latencia
- Incidencias detectadas
- Acta final de aceptación o rechazo

---

## 8. Criterios de Aceptación Global

**ACEPTADO** si se cumplen simultáneamente:
1. Todos los casos críticos CP-01 a CP-05 superados
2. No existen fallos críticos abiertos sobre captura, integridad o enforcement
3. Los KPIs mínimos se encuentran dentro de umbral
4. La evidencia generada es suficiente para reconstrucción de auditoría
5. El cliente valida funcionalmente el flujo end-to-end

**ACEPTADO CON RESERVAS** si:
- Existen fallos no críticos documentados
- No afectan captura, integridad ni policy enforcement
- Tienen plan de remediación acordado

**RECHAZADO** si falla cualquiera de:
- Captura por debajo de umbral
- Incapacidad de detectar manipulación
- Ausencia de evidencia exportable
- Políticas críticas que no bloquean o no marcan
- Imposibilidad de reconstruir un evento bajo consulta de auditoría

---

## 9. Acta de Cierre

**Resultado final:** ☐ ACEPTADO · ☐ ACEPTADO CON RESERVAS · ☐ RECHAZADO

**Observaciones:**
_[Texto]_

**Incidencias abiertas:**
_[Texto]_

| Rol | Nombre | Firma | Fecha |
| :--- | :--- | :--- | :--- |
| Responsable cliente | __________________ | __________________ | __________________ |
| Responsable técnico | __________________ | __________________ | __________________ |

---

*Validamos CORTEX con un protocolo de aceptación basado en 4 pruebas: captura de eventos automáticos, integridad frente a manipulación, enforcement de políticas críticas, y respuesta de auditoría con reconstrucción verificable en minutos. Si no pasa esas cuatro, no se vende como compliance operativo.*
