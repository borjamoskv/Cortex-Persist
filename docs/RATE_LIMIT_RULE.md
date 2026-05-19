# CORTEX-Persist 429 Error Resolution (C5-REAL)

## Diagnóstico C5-REAL
```yaml
diagnostico_C5:
  error: HTTP_429_TOO_MANY_REQUESTS
  status: RESOURCE_EXHAUSTED
  certeza:
    C5_REAL:
      - el_endpoint_devolvio_HTTP_429
      - el_payload_indica_RESOURCE_EXHAUSTED
      - el_mensaje_indica_agotamiento_de_recurso_o_cuota
      - la_respuesta_usa_text/event-stream
      - existe_trace_id_y_trajectory_id_para_soporte
    C4_INFERENCIA_PROBABLE:
      - exceso_de_requests_en_paralelo
      - exceso_de_streaming
      - limite_RPM_TPM_RPD_alcanzado
      - retry_loop_demasiado_agresivo
      - fanout_agentico_demasiado_alto
  no_es_deducible_solo_con_este_payload:
    - bug_del_prompt
    - fallo_de_Lean
    - fallo_del_skill
    - error_de_sintaxis
    - fallo_logico_del_modelo
  lectura:
    resumen: "El sistema no ha rechazado la tarea por contenido ni por sintaxis; ha rechazado la carga por límite de recursos."
    accion_correcta: "throttle + backoff + concurrency cap + checkpoint resume"
```

## Lectura del error

El payload dice:

```json
{
  "error": {
    "code": 429,
    "message": "Resource has been exhausted (e.g. check quota).",
    "status": "RESOURCE_EXHAUSTED"
  }
}
```

Interpretación:

```yaml
hecho:
  http_code: 429
  meaning: Too Many Requests
hecho:
  provider_status: RESOURCE_EXHAUSTED
  meaning: recurso/cuota/límite consumido
inferencia_probable:
  causa: demasiada_concurrencia_o_cuota_insuficiente
evidencia_operativa:
  trace_id: "0xa51618cbd72a9520"
  trajectory_id: "25a9ca11-92a4-4f46-9343-1933796d1116"
  content_type: "text/event-stream"
```

## Acción inmediata

```yaml
fix_inmediato:
  - detener_reintentos_inmediatos
  - activar_exponential_backoff_con_jitter
  - reducir_concurrency_a_1_3
  - limitar_requests_por_minuto
  - guardar_trace_id_y_trajectory_id
  - reanudar_desde_checkpoint
  - revisar_quota_billing_limits_del_provider
no_hacer:
  - lanzar_mas_agentes
  - abrir_mas_streams
  - repetir_el_mismo_loop_sin_backoff
  - asumir_que_el_prompt_fallo
```

## Regla dura

```yaml
si_ves:
  - HTTP_429
  - RESOURCE_EXHAUSTED
  - Too_Many_Requests
  - check_quota
entonces:
  hacer:
    - throttle
    - exponential_backoff
    - reducir_concurrency
    - guardar_trace_id
    - reanudar_desde_checkpoint
    - comprobar_quota
  no_hacer:
    - retry_inmediato
    - aumentar_agents
    - abrir_mas_streams
    - relanzar_loop_completo
    - diagnosticar_como_bug_del_prompt
```

## Versión ultra corta

```yaml
veredicto:
  C5_REAL:
    error: HTTP_429_TOO_MANY_REQUESTS
    status: RESOURCE_EXHAUSTED
    significado: limite_de_recurso_o_cuota_alcanzado
  C4_PROBABLE:
    causa: exceso_de_concurrencia_o_reintentos
  fix:
    - backoff
    - concurrency_cap
    - circuit_breaker
    - checkpoint_resume
    - quota_check
  trace_para_soporte:
    trace_id: "0xa51618cbd72a9520"
    trajectory_id: "25a9ca11-92a4-4f46-9343-1933796d1116"
```

**Veredicto final:** No hay evidencia de que CORTEX, Lean, el prompt o el skill hayan fallado. La evidencia disponible indica saturación de cuota o rate limit. Baja fanout, aplica backoff, limita streams y reanuda desde checkpoint.
