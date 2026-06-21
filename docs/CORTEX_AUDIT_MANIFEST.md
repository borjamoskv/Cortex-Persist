# CORTEX: THE AUDIT & EVIDENCE LAYER

> **Reality Level:** `C5-REAL` (Computational Evidence & Reproducibility)
> **Aesthetic:** `Industrial Noir 2026`

## 1. LA LEY DE HIERRO DE LA AUDITORÍA C5-REAL

En auditoría, cien campos de `meta`, `tags`, `flags` o *vibes* valen exactamente cero. La única realidad es la matemática de la ejecución.

### Reglas Absolutas:
1. **Si no se puede recomputar, no cuenta.**
2. **Si falta evidencia, se falla (Hard Fail).**

---

## 2. EL MANIFIESTO DE EVIDENCIA (Evidencia > Confeti)

Todo agente, proceso o flujo en MOSKV-1 y CORTEX PERSIST debe aportar **estas piezas exactas** para ser considerado válido bajo auditoría. Nada menos es aceptable:

1. **Prueba recomputable**: Poder repetir el proceso y llegar al mismo resultado (Determinismo absoluto).
2. **Commit exacto + tree SHA**: La prueba debe anclarse al árbol exacto en Git. No se audita "más o menos ese código", sino el hash criptográfico del árbol completo.
3. **Working tree limpio**: La ejecución de la prueba debe realizarse sin basura local o archivos no trackeados contaminando el veredicto.
4. **Hash del artefacto final**: Huella SHA-256 del objeto generado (ej. binario, payload, documento). Poesía sobre el objeto no es evidencia.
5. **Cadena de custodia completa**: Pipeline observable: Commit → Build → Runtime → Output. Si un eslabón falta, la cadena se considera rota.
6. **Fallo explícito (`raise`)**: Cuando falta evidencia o se viola un constraint, el sistema explota de forma escandalosa. Prohibido el maquillaje, el silenciado de excepciones (`except Exception: pass`) o el "Green Theater".
7. **Firma verificable**: El artefacto resultante debe tener integridad criptográfica comprobable localmente (ej. firma Ed25519 o `CORTEX-TAINT` estricto).
8. **Timestamp UTC**: Registro temporal centralizado y sin sesgo de zona local (relojes borrachos).
9. **Binario ejecutado + hash**: Si se compila/ejecuta, la auditoría requiere el hash del binario resultante, no solo del script fuente.
10. **Salida cruda del verificador**: El volcado íntegro de la terminal/log. El testimonio sin cosmética (nada de summaries endulzados por LLMs).
11. **Diff mínimo y legible**: La cirugía de código. Un delta atómico que pueda ser revisado humanamente sin sobrecarga cognitiva (El mural vs. El escalpelo).
12. **Unidades y método de medida explícitos**: *Throughput* (ej. operaciones/sec) no es *Latency* (ej. ms). Si mezclas unidades, pierdes el significado físico y la métrica se anula.
13. **Evidencia externa independiente**: La evidencia debe existir en Git, en el CI o en un Ledger auditable que esté matemáticamente separado del relato del modelo generativo.
14. **Reproducibilidad en máquina nueva**: Si el entorno o build no corre fuera de tu configuración local alterada, no es auditoría.
15. **Contadores coherentes**: Las cifras deben derivar de registros de sistema en memoria o disco. 100 no es 10,000 por deseo o por alucinación probabilística.

---

## 3. COMPORTAMIENTO ESPERADO DEL KERNEL

Al integrar estos 15 puntos en `cortex.audit.ledger` y en las fronteras de mutación (`cortex/engine/crystallizer.py`):
- Todo nodo procesado emitirá el payload validado o provocará la inyección de apoptosis termodinámica en el thread.
- La reconstrucción del Ledger se hará validando hashes encadenados hacia atrás.
