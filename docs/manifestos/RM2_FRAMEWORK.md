<!-- [C5-REAL] Exergy-Maximized -->
# Framework RM² (Memory-Constrained Adaptive Inference)

> Formulación matemática definitiva del framework RM² como un problema clásico de inferencia secuencial con memoria limitada. El centro de gravedad pasa de la heurística y la metáfora a la optimización bajo restricciones.

## 1. Formulación del Problema (Memory-Constrained POMDP)
El sistema se define por la tupla: \((\mathcal{S}, \mathcal{A}, \mathcal{O}, T, R, \mathcal{M}, B, \pi)\)
- \(\mathcal{S}, \mathcal{A}, \mathcal{O}\): Espacios de Estados, Acciones y Observaciones.
- \(T, R\): Función de Transición \(P(s' | s, a)\) y Función de Recompensa.
- \(\mathcal{M}\): Espacio de estados de memoria, donde cada \(M_t = \{H_1, \dots, H_n\}\) es el conjunto de hipótesis activas.
- \(B\): Presupuesto computacional acotado.
- \(\pi(a, a_{mem} | M_t, O_t)\): Política que define simultáneamente la acción ambiental (\(a\)) y la acción de gestión de memoria (\(a_{mem}\): evicciones).

**El Objetivo Formal:** Maximizar la recompensa esperada \(\mathbb{E}[\sum \gamma^t R_t]\) sujeta a la restricción absoluta \(\sum_{i \in M_t} c_i \le B, \forall t\).

---

## 2. Dinámica Temporal (Actualización de Estado)
Si la probabilidad posterior y la utilidad fuesen estáticas, no habría aprendizaje. Ambas deben evolucionar dinámicamente con cada observación \(O_t\):

### Actualización de Probabilidad (Inferencia Bayesiana Secuencial)
\[ p_{i, t+1} = \frac{P(O_t | H_i) p_{i, t}}{\sum_{j} P(O_t | H_j) p_{j, t}} \]
Las hipótesis cuya verosimilitud para explicar la evidencia \(O_t\) es baja, ven su \(p_i\) decrecer asintóticamente.

### Estimación de Utilidad (Ecuación de Bellman / Information Gain)
La utilidad (\(u_i\)) de retener una hipótesis no es intrínseca, sino predictiva. Se estima iterativamente como el valor Q de retener esa hipótesis:
\[ u_{i, t+1} = \alpha \cdot \text{InformationGain}(H_i, O_t) + (1 - \alpha) \cdot \mathbb{E}[V(M_{t+1}) | H_i \in M_{t+1}] \]
Donde la ganancia de información se mide como la divergencia Kullback-Leibler entre prior y posterior.

---

## 3. Justificación Matemática del Criterio de Evicción
El problema de determinar qué subconjunto de hipótesis retener en \(M_t\) que maximice el valor esperado \(\sum (p_i u_i)\) sin superar el coste \(\sum c_i \le B\) es isomorfo al **Problema de la Mochila 0-1 (0-1 Knapsack Problem)**.

Al aplicar la relajación fraccional (Fractional Knapsack) para aproximar la política de evicción (\(a_{mem}\)) en tiempo real, la estrategia avara (greedy) matemática y demostrablemente óptima dicta ordenar los elementos por su **ratio valor/peso**.

Por lo tanto, el criterio de prioridad para el Semantic GC **no es una heurística de diseño**, es la solución formal de optimización:
\[ S_i = \frac{\text{Expected Value}}{\text{Cost}} = \frac{p_i u_i}{c_i} \]
El sistema purga sistemáticamente el final de la cola ordenada por \(S_i\) hasta satisfacer la restricción \(B\).

---

## 4. Presupuesto Explícito de Exploración
Para evitar la convergencia estéril a un óptimo local del subespacio de hipótesis evaluadas (asfixia del POMDP), la política de memoria \(\pi\) reserva un presupuesto inamovible \(\epsilon > 0\) (donde \(\epsilon\) forma parte del presupuesto global \(B\)) destinado exclusivamente a la retención de hipótesis generativas (alto \(c_i\), baja \(p_i\) inicial).

Esto desacopla la necesidad de explorar de la estimación recursiva del Expected Value of Information, rompiendo la circularidad del *bootstrapping*.

---

## 5. Garantías Teóricas a Demostrar
La formalización del framework RM² permite ahora exigir la demostración de los siguientes teoremas matemáticos:

1. **Regret Sublineal**: Bajo \(\epsilon\)-exploración y evicción \(\mathcal{O}(S_i)\), la política de memoria \(\pi\) incurre en un *regret* asintótico de memoria \(\mathcal{O}(\sqrt{T})\) en comparación con un oráculo con memoria ilimitada \(B = \infty\).
2. **Convergencia del Subespacio Activo**: Tras suficientes evidencias \(O_t\), la distancia de Wasserstein entre \(M_t\) y la distribución posterior real de hipótesis está acotada.
3. **Estabilidad de la Capacidad (\(B\))**: El coste total \(C(M_t)\) nunca viola la condición de restricción bajo variaciones arbitrarias del entorno, evitando caídas (OOM/Latencia máxima).

---
> **Conclusión**: El olvido agresivo ya no es una analogía; es la aplicación forzosa de la solución óptima del *Knapsack Problem* a un *POMDP* con memoria finita. Las intuiciones quedan descartadas; solo las matemáticas C5-REAL rigen la retención de estado en CORTEX-Persist.
