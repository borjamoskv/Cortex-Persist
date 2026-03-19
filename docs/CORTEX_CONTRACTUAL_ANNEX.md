# ANEXO — Protocolo Contractual de Aceptación de CORTEX

**Entre**
[CLIENTE], con domicilio en [●] y NIF/CIF [●]
**y**
[PROVEEDOR], con domicilio en [●] y NIF/CIF [●]

**Vinculado al contrato principal:** [Nombre / referencia del contrato]
**Fecha:** [●]
**Versión del anexo:** 1.0

---

## 1. Objeto

El presente Anexo regula el procedimiento, criterios, evidencias y efectos contractuales de la aceptación de la solución CORTEX por parte del CLIENTE.

A efectos de este Anexo, la aceptación tendrá por objeto verificar que CORTEX funciona conforme a los requisitos funcionales y técnicos pactados para:

- captura automática de eventos;
- trazabilidad y correlación;
- integridad y detección de manipulación;
- enforcement de políticas configuradas;
- consulta y exportación para auditoría;
- diferenciación entre evidencia nativa y evidencia reconstruida;
- y rendimiento operativo básico.

La aceptación se limita a la verificación de dichas capacidades y no implica garantía de cumplimiento regulatorio integral por sí sola, ni sustituye el análisis jurídico, organizativo o documental que corresponda al CLIENTE.

---

## 2. Definiciones

A efectos de este Anexo:

**"CORTEX"** significa la solución software, módulos, conectores, configuraciones y componentes auxiliares suministrados por el PROVEEDOR.

**"Entorno de Aceptación"** significa el entorno de staging, preproducción o producción controlada designado por las Partes para la ejecución de las pruebas.

**"Caso de Prueba"** significa cada supuesto funcional o técnico descrito en este Anexo.

**"Incidencia Crítica"** significa cualquier defecto que impida o degrade materialmente cualquiera de estas capacidades: captura automática, integridad, enforcement de políticas críticas o reconstrucción auditable del evento.

**"Incidencia No Crítica"** significa cualquier defecto que no impida el uso sustancial de CORTEX para los fines definidos en este Anexo.

**"Evidencia Nativa"** significa el registro originado automáticamente por CORTEX a partir de su activación operativa.

**"Evidencia Reconstruida"** significa el registro generado por importación, reconciliación o reconstrucción a partir de fuentes técnicas previas ajenas o anteriores a CORTEX.

**"Aceptación"** significa la conformidad contractual del CLIENTE con el resultado de las pruebas conforme a las reglas del presente Anexo.

---

## 3. Alcance de la aceptación

La aceptación cubrirá exclusivamente los siguientes dominios:

1. Captura automática de eventos
2. Trazabilidad y correlación de eventos
3. Integridad y detección de alteraciones
4. Enforcement de políticas críticas
5. Consulta, búsqueda y exportación de evidencia
6. Gestión diferenciada de evidencia nativa y reconstruida
7. Compatibilidad con los backends/modelos incluidos en el Alcance
8. Rendimiento operativo básico

Quedan fuera del alcance de este Anexo, salvo pacto expreso en contrario:

- clasificación regulatoria del sistema del CLIENTE;
- asesoramiento jurídico;
- auditorías regulatorias formales;
- validación de exactitud material del modelo de IA;
- disponibilidad de terceros;
- y requisitos no documentados en el Contrato o en este Anexo.

---

## 4. Entorno, medios y colaboración del CLIENTE

### 4.1 Entorno

El CLIENTE pondrá a disposición, en plazo, el Entorno de Aceptación con los accesos, credenciales, datasets, conectividad, logs previos y configuraciones razonablemente necesarios para ejecutar las pruebas.

### 4.2 Dependencias del CLIENTE

Cuando la ejecución de una prueba dependa de sistemas, APIs, redes, repositorios, identidades, almacenamientos o servicios del CLIENTE o de terceros bajo su control, cualquier imposibilidad, retraso o degradación atribuible a tales elementos suspenderá el cómputo del plazo de aceptación respecto de las pruebas afectadas.

### 4.3 Responsables

Cada Parte designará por escrito:

- un responsable técnico;
- y un responsable de validación.

---

## 5. Fases del procedimiento de aceptación

### 5.1 Despliegue

Instalación o habilitación de CORTEX en el Entorno de Aceptación.

### 5.2 Configuración inicial

Carga de políticas, parametrización, activación de logging, definición de conectores y preparación de usuarios de prueba.

### 5.3 Ejecución de pruebas

Ejecución de los Casos de Prueba descritos en la cláusula 8.

### 5.4 Emisión de evidencias

Generación y entrega al CLIENTE de la evidencia resultante.

### 5.5 Revisión

El CLIENTE dispondrá del plazo indicado en la cláusula 11 para revisar resultados y comunicar:

- aceptación;
- aceptación con reservas;
- o rechazo motivado.

---

## 6. Principios de aceptación

### 6.1 Verificación por evidencia

Ninguna funcionalidad se considerará aceptada por mera declaración verbal o documental; deberá existir evidencia objetiva y verificable.

### 6.2 Reproducibilidad

Los resultados deberán poder reproducirse razonablemente en el Entorno de Aceptación.

### 6.3 Separación entre pasado y futuro

Las Partes reconocen expresamente que CORTEX:

- genera Evidencia Nativa desde su activación;
- puede procesar o reconstruir histórico cuando existan fuentes técnicas previas;
- pero no crea retroactivamente registro originario de periodos anteriores en los que no haya existido captura automática.

### 6.4 No garantía absoluta

El PROVEEDOR no garantiza la ausencia de cualquier incidente, sanción, requerimiento o inspección, sino el funcionamiento de CORTEX conforme a los criterios de aceptación pactados.

---

## 7. Requisitos previos a las pruebas

Antes de iniciar la aceptación, deberán verificarse como mínimo:

- CORTEX desplegado en el Entorno de Aceptación
- Logging habilitado
- Almacenamiento de evidencia disponible
- Sincronización horaria del entorno
- Usuarios de prueba creados
- Dataset sintético disponible
- Políticas mínimas cargadas
- Acceso a los backends/modelos incluidos en alcance
- Mecanismo de exportación habilitado

La falta de cualquiera de los anteriores podrá justificar la reprogramación de las pruebas sin penalización para el PROVEEDOR.

---

## 8. Casos de prueba contractuales

### CP-01 — Captura automática de eventos

**Objetivo:** Verificar que CORTEX registra automáticamente los eventos relevantes generados por el sistema.

**Procedimiento mínimo:**
1. Ejecutar un lote de inferencias de prueba
2. Registrar el número de eventos emitidos por el sistema fuente
3. Consultar el número de eventos capturados por CORTEX
4. Reconciliar ambos conjuntos

**Criterios mínimos:**
- `capture_rate >= 99,8%`
- `orphan_log_rate <= 0,1%`
- Ausencia de duplicados no justificados

**Evidencia mínima:** reporte de ejecución, export de logs, reconciliación fuente vs. CORTEX.

---

### CP-02 — Trazabilidad y correlación

**Objetivo:** Verificar que cada evento puede localizarse y correlacionarse de forma unívoca.

**Procedimiento mínimo:**
1. Seleccionar una muestra de eventos
2. Consultar por trace_id, ventana temporal, actor y backend
3. Verificar la correlación input → output → revisión, cuando aplique

**Criterio mínimo:**
- 100% de los eventos muestreados deben ser localizables y correlacionables

**Evidencia mínima:** consultas ejecutadas, export o capturas, informe de correlación.

---

### CP-03 — Integridad y detección de manipulación

**Objetivo:** Verificar que una alteración posterior es detectable.

**Procedimiento mínimo:**
1. Generar lote de eventos
2. Obtener snapshot o mecanismo de verificación de integridad
3. Alterar un evento en entorno controlado
4. Reejecutar la verificación

**Criterio mínimo:**
- 100% de las alteraciones intencionadas deben ser detectadas

**Evidencia mínima:** snapshot previo, snapshot posterior, reporte de verificación, alerta o marca de inconsistencia.

---

### CP-04 — Enforcement de políticas críticas

**Objetivo:** Verificar que CORTEX bloquea, marca o alerta en los supuestos definidos.

**Escenarios mínimos:**
- Inferencia sin logging activo
- Backend o modelo no aprobado
- Falta de metadata obligatoria
- Output crítico sin revisor, cuando la política lo requiera
- Intento de borrado fuera de política de retención

**Criterio mínimo:**
- 100% de los escenarios críticos deben provocar la respuesta esperada

**Evidencia mínima:** logs de policy, alertas, bloqueos o marcas, reporte de resultados.

---

### CP-05 — Consulta y export para auditoría

**Objetivo:** Verificar que un evento puede reconstruirse y exportarse con rapidez razonable.

**Procedimiento mínimo:**
1. Simular una solicitud de auditoría
2. Buscar eventos por sistema, fecha, backend y actor
3. Exportar el resultado
4. Verificar su integridad según el diseño implantado

**Criterios mínimos:**
- Tiempo de consulta: < 30 segundos
- Tiempo de export: < 2 minutos
- Paquete exportado verificable y completo

**Evidencia mínima:** query ejecutada, export generado, medición temporal, reporte de verificación.

---

### CP-06 — Evidencia reconstruida

**Objetivo:** Verificar la separación entre evidencia nativa y reconstruida.

**Procedimiento mínimo:**
1. Importar lote histórico desde fuentes previas
2. Confirmar marcado como reconstruido
3. Ejecutar consultas mixtas

**Criterios mínimos:**
- 100% del histórico importado marcado como reconstruido
- 0 eventos nativos etiquetados erróneamente como reconstruidos

**Evidencia mínima:** informe de importación, muestra de eventos, consultas de verificación.

---

### CP-07 — Compatibilidad multi-backend

**Objetivo:** Verificar que el esquema de trazabilidad se mantiene estable en los modelos o backends incluidos en alcance.

**Procedimiento mínimo:**
1. Ejecutar el mismo set de casos sobre cada backend incluido
2. Comparar estructura y completitud de logs

**Criterio mínimo:**
- Consistencia estructural razonable entre backends
- 100% de campos obligatorios presentes

**Evidencia mínima:** export comparativo, diff o informe técnico.

---

### CP-08 — Rendimiento operativo básico

**Objetivo:** Verificar que CORTEX no introduce degradación inaceptable.

**Métricas mínimas:** latencia adicional por evento, tiempo de consulta p95, tiempo de export, tasa de error.

**Criterios mínimos:**
- `audit_query_latency_p95 < 30s`
- `export_success_rate >= 99,9%`
- Overhead dentro del umbral acordado por las Partes

**Evidencia mínima:** benchmark, métricas p50/p95/p99, reporte de errores.

---

## 9. KPIs contractuales de aceptación

| KPI | Umbral mínimo |
| :--- | :--- |
| Capture Rate | ≥ 99,8% |
| Orphan Log Rate | ≤ 0,1% |
| Tamper Detection Rate | = 100% |
| Policy Critical Detection Rate | = 100% |
| Export Success Rate | ≥ 99,9% |
| Audit Query Latency p95 | < 30s |
| Historical Labeling Accuracy | = 100% |

Los KPI se medirán exclusivamente sobre el Entorno de Aceptación y sobre las pruebas ejecutadas conforme a este Anexo.

---

## 10. Evidencia obligatoria

Al finalizar las pruebas, el PROVEEDOR entregará o pondrá a disposición:

- Plan de pruebas ejecutado
- Dataset sintético o referencia del dataset
- Configuración del entorno
- Versión exacta de CORTEX
- Resultados por Caso de Prueba
- Exportaciones JSON, CSV o equivalentes
- Snapshots o reportes de integridad
- Logs de policy
- Métricas de latencia y error
- Relación de incidencias detectadas
- Propuesta de remediación, en su caso

---

## 11. Plazo de revisión y silencio

### 11.1 Plazo

El CLIENTE dispondrá de [5/10/15] Días Hábiles desde la entrega de evidencias para revisar y comunicar por escrito: aceptación, aceptación con reservas, o rechazo motivado.

### 11.2 Silencio

Si transcurrido dicho plazo el CLIENTE no hubiera comunicado por escrito objeciones materiales y motivadas, la solución se considerará aceptada tácitamente.

### 11.3 Rechazo motivado

Todo rechazo deberá identificar de forma concreta:

- Caso(s) de Prueba afectados
- Evidencia revisada
- Defecto observado
- Impacto
- Motivo por el que constituye Incidencia Crítica

No se admitirán rechazos genéricos, indeterminados o basados en requisitos no incluidos en este Anexo.

---

## 12. Resultado de la aceptación

### 12.1 Aceptación

CORTEX quedará **ACEPTADO** cuando:

1. Se superen CP-01 a CP-05
2. No existan Incidencias Críticas abiertas
3. Los KPI mínimos queden dentro de umbral
4. Exista evidencia suficiente para reconstrucción auditada del evento

### 12.2 Aceptación con Reservas

CORTEX podrá quedar **ACEPTADO CON RESERVAS** cuando existan Incidencias No Críticas que:

- No afecten captura, integridad, enforcement crítico ni consulta auditable
- Estén documentadas
- Dispongan de plan y plazo de remediación acordados

La Aceptación con Reservas no impedirá la facturación, salvo pacto expreso en contrario.

### 12.3 Rechazo

CORTEX quedará **RECHAZADO** únicamente si concurre alguna de estas circunstancias:

- `capture_rate` por debajo del umbral contractual
- Imposibilidad de detectar alteración intencionada
- Ausencia de evidencia exportable en CP-05
- Fallo en políticas críticas de CP-04
- Imposibilidad de reconstruir un evento de prueba conforme a este Anexo

---

## 13. Subsanación y nueva prueba

### 13.1 Subsanación

En caso de Rechazo motivado, el PROVEEDOR dispondrá de [10/15/20] Días Hábiles para subsanar las Incidencias Críticas identificadas.

### 13.2 Re-test

Subsanadas las Incidencias Críticas, se repetirá únicamente la prueba afectada y aquellas otras razonablemente impactadas por la corrección.

### 13.3 Límite

Salvo pacto distinto, el procedimiento de subsanación y re-test se realizará hasta un máximo de [2] ciclos antes de aplicar los remedios contractuales que correspondan.

---

## 14. Efectos contractuales de la aceptación

**La Aceptación supondrá:**

- Conformidad funcional y técnica dentro del alcance de este Anexo
- Habilitación de la facturación vinculada al hito de aceptación, en su caso
- Inicio del periodo de soporte, garantía o mantenimiento previsto en el Contrato Principal, si aplica

**La Aceptación no supondrá:**

- Reconocimiento de cumplimiento regulatorio integral del CLIENTE
- Renuncia a derechos frente a vicios ocultos o incumplimientos posteriores
- Aceptación de prestaciones no incluidas en el alcance

---

## 15. Limitación específica sobre cumplimiento regulatorio

Las Partes reconocen expresamente que:

1. CORTEX es una capa técnica de trazabilidad, evidencia y enforcement
2. Su aceptación contractual acredita el funcionamiento de dichas capacidades según este Anexo
3. Pero no constituye por sí misma certificación legal, auditoría regulatoria ni garantía absoluta de ausencia de sanciones

Cualquier referencia comercial a reducción de exposición regulatoria, mejora de auditabilidad o fortalecimiento de la posición probatoria deberá interpretarse en ese sentido técnico-operativo y no como promesa de inmunidad jurídica.

---

## 16. Confidencialidad de la evidencia

Toda evidencia, export, log, snapshot, dataset o material generado en el marco de la aceptación tendrá la consideración de Información Confidencial, salvo que el Contrato Principal disponga otra cosa.

El uso de dicha evidencia quedará limitado a: validación contractual, auditoría interna, cumplimiento, gestión de incidencias, y defensa de derechos de cualquiera de las Partes.

---

## 17. Orden de prevalencia

En caso de contradicción entre este Anexo y el Contrato Principal:

1. Prevalecerá el Contrato Principal en materias económicas, de responsabilidad, confidencialidad, protección de datos y terminación
2. Prevalecerá este Anexo en lo relativo al procedimiento y criterios de aceptación técnica

---

## 18. Firma / Acta final

**Resultado final:** ☐ ACEPTADO · ☐ ACEPTADO CON RESERVAS · ☐ RECHAZADO

**Observaciones:**
_[●]_

**Incidencias abiertas:**
_[●]_

| | Nombre | Cargo | Firma | Fecha |
| :--- | :--- | :--- | :--- | :--- |
| **Por el CLIENTE** | __________________ | __________________ | __________________ | __________________ |
| **Por el PROVEEDOR** | __________________ | __________________ | __________________ | __________________ |

---

## Cláusula corta para insertar en contrato marco

> **Aceptación de CORTEX.** La aceptación de CORTEX se realizará conforme al Anexo de Aceptación aplicable. La solución se considerará aceptada cuando supere las pruebas de captura automática, trazabilidad, integridad, enforcement de políticas críticas y consulta/exportación auditables allí previstas, o cuando el CLIENTE no formule objeciones materiales y motivadas dentro del plazo de revisión pactado. La aceptación acredita el funcionamiento técnico de la solución dentro del alcance contratado, pero no constituye certificación legal ni garantía absoluta de cumplimiento regulatorio integral.
