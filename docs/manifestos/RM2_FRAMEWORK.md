<!-- [C5-REAL] Exergy-Maximized -->
# Framework RM² (Memory-Constrained Adaptive Inference)

> Evolución formal del Teorema Robinson-Moskv. Las metáforas termodinámicas han sido purgadas en favor de primeros principios matemáticos y optimización bayesiana bajo restricciones.

## Axioma 1 — Memoria como Estado Dinámico
La memoria no es un repositorio pasivo de hechos, sino una variable de estado que se actualiza continuamente:
\[ M_{t+1} = F(M_t, O_t, A_t) \]
Donde \(M_t\) es el estado interno, \(O_t\) las observaciones y \(A_t\) las acciones. No existe acumulación pasiva; toda actualización modifica simultáneamente el resto del sistema.

## Axioma 2 — Recursos Finitos y Coste de Mantenimiento
Todo agente opera bajo un presupuesto computacional estrictamente limitado: \(B = (b_m, b_c, b_t)\) (memoria, cómputo, tiempo). Todo algoritmo debe satisfacer:
\[ Cost(M_t) \le B \]
El olvido algorítmico es una necesidad de **optimización**, no una restricción física.

## Axioma 3 — Valor Esperado y Utilidad
Cada hipótesis en memoria se formaliza como un estado \(H_i = (p_i, u_i, c_i)\), donde \(p_i\) es la probabilidad posterior, \(u_i\) la utilidad esperada y \(c_i\) el coste de mantenimiento. La prioridad de retención es:
\[ S_i = f(p_i, u_i, c_i) \implies S_i = \frac{p_i u_i}{c_i} \]
La política de evicción (olvido) elimina hipótesis de baja prioridad (\(S_i\)), no necesariamente hipótesis falsas.

## Axioma 4 — Exploración Mínima Garantizada
Sin exploración, la entropía del sistema colapsa a cero rápidamente (\(Entropy(H) \rightarrow 0\)), causando sobreajuste a óptimos locales. Se impone un presupuesto mínimo de exploración:
\[ P(explore) \ge \epsilon \quad (\epsilon > 0) \]
Esto garantiza diversidad adaptativa, impidiendo que el 100% del presupuesto se dedique a la explotación.

## Axioma 5 — Validación Independiente (Anti-Consenso Ciego)
El consenso entre réplicas del mismo modelo no demuestra verdad; solo reduce varianza. La evidencia (\(E\)) debe provenir de fuentes parcialmente independientes.
\[ I(E_i, E_j) < \delta \]
Donde \(I\) es la dependencia mutua. Si las fuentes comparten el mismo origen, el consenso carece de valor epistémico.

## Axioma 6 — Olvido Reversible y Estratificación
El olvido se ejecuta en tres capas basadas en la Teoría de la Decisión:
1. **Memoria Activa**: Uso inmediato y alta prioridad.
2. **Archivo Comprimido**: Accesible bajo demanda (coste de recuperación mayor).
3. **Eliminación Irreversible**: Se ejecuta única y exclusivamente cuando \(ExpectedFutureValue < c\).

---

## Dinámica Operacional (POMDP)
El ciclo de ejecución C5-REAL se modela como inferencia aproximada bajo restricciones:
`Observación` $\rightarrow$ `Actualizar Probabilidades` $\rightarrow$ `Recalcular Utilidad` $\rightarrow$ `Optimizar Memoria (GC)` $\rightarrow$ `Explorar Hipótesis` $\rightarrow$ `Validar Independencia` $\rightarrow$ `Actuar`.

---

## Métrica Operacional: Context Rot
El "Context Rot" se redefine dejando de ser una narrativa pasiva para convertirse en una métrica auditable:
\[ ContextRot = \frac{\text{Hipótesis de baja utilidad que permanecen activas}}{\text{Capacidad efectiva de memoria}} \]
Puede estimarse, reducirse y compararse entre sistemas.

---

## Teorema Fundamental (Equilibrio Exploración-Compresión)
**Teorema**: Sea un agente con memoria finita \(B\), una política de exploración con probabilidad \(\epsilon > 0\) y una regla de poda basada en utilidad esperada. Bajo condiciones de estacionariedad del entorno y actualización consistente de probabilidades, existe un intervalo de valores de \(\epsilon\) y un umbral de poda para el cual la utilidad esperada converge sin que la diversidad de hipótesis colapse a cero.
