<!-- [C5-REAL] Exergy-Maximized -->
# Framework RM² (Memory-Constrained Adaptive Inference)

> Formulación matemática definitiva del framework RM² como un problema clásico de inferencia secuencial con memoria limitada. El centro de gravedad pasa de la heurística y la metáfora a la optimización bajo restricciones.

## 1. Definiciones Formales (Especificación del Modelo)

### El POMDP con Memoria Finita
El sistema se define rigurosamente mediante la tupla: \((\mathcal{S}, \mathcal{A}, \mathcal{O}, T, R, \mathcal{M}, B, \pi)\)
- \(\mathcal{S}, \mathcal{A}, \mathcal{O}\): Espacios de Estados, Acciones y Observaciones.
- \(T, R\): Función de Transición \(P(s' | s, a)\) y Función de Recompensa.
- \(\mathcal{M}\): Espacio de estados de memoria. Cada \(M_t \subset \mathcal{M}\) se formaliza como un **grafo topológico ponderado** de hipótesis interdependientes, no un simple conjunto plano.
- \(B\): Presupuesto computacional acotado.
- \(G\): Operador de Transición de Memoria explícito, \(M_{t+1} = G(M_t, O_t, a_{mem})\), que rige la mutación topológica post-evicción.
- \(\pi(a, a_{mem} | M_t, O_t)\): Política conjunta que emite la acción ambiental (\(a\)) y la poda de nodos en el grafo de memoria (\(a_{mem}\)).

**El Objetivo Formal:** Maximizar el valor esperado descontado infinito:
\[ V^\pi(s_0, M_0) = \mathbb{E}_\pi \left[ \sum_{t=0}^{\infty} \gamma^t R_t \;\Big|\; s_0, M_0 \right] \]
Sujeto invariablemente a la restricción absoluta de capacidad:
\[ C(M_t) = \sum_{i \in M_t} c_i \le B, \quad \forall t \]

---

## 2. Propuestas Algorítmicas (Inferencia y Optimización)

### Actualización de Probabilidad (Inferencia Bayesiana)
Las hipótesis se filtran frente a la evidencia secuencial:
\[ p_{i, t+1} \propto P(O_t | H_i) p_{i, t} \]

### Estimación de Utilidad Unificada
La utilidad \(u_i\) de retener \(H_i\) se deriva exclusivamente de su contribución a la recompensa futura. \(u_i\) mide estrictamente el Delta del valor futuro (Advantage) provisto por la retención de la hipótesis en la memoria:
\[ u_{i, t} = \mathbb{E}_{\pi} \left[ \sum_{k=0}^{\infty} \gamma^k R_{t+k} \;\Big|\; H_i \in M_{t} \right] - \mathbb{E}_{\pi} \left[ \sum_{k=0}^{\infty} \gamma^k R_{t+k} \;\Big|\; H_i \notin M_{t} \right] \]

### El Criterio de Evicción (Fractional Knapsack)
El problema instantáneo de decidir qué subgrafo retener se resuelve aproximando una política avara (greedy):
\[ S_i = \frac{\text{Expected Advantage}}{\text{Cost}} = \frac{p_i u_i}{c_i} \]

**Condiciones de Optimalidad Exacta**: Este criterio \(S_i\) es una heurística eficiente. Para considerarse la solución óptima del proceso secuencial, requeriría supuestos estrictos:
1. Independencia probabilística absoluta entre hipótesis en \(\mathcal{M}\).
2. Utilidad estrictamente aditiva (ausencia de submodularidad o efectos de interacción).
3. Costes \(c_i\) marginales constantes e independientes del estado de la memoria.
4. El descarte de \(H_i\) no modifica drásticamente las dinámicas de transición futuras del POMDP.
Bajo la relajación natural de estos supuestos, \(S_i\) actúa como una heurística de aproximación.

### Presupuesto Explícito de Exploración
Para evitar la convergencia estéril a un óptimo local del subespacio de hipótesis, la política \(\pi\) reserva un presupuesto inamovible \(\epsilon > 0\) destinado exclusivamente a la retención de hipótesis generativas (alto \(c_i\), baja \(p_i\) inicial).

---

## 3. Primitivas de Colisión e Invariantes Operacionales

### Definición 3.1 (Operador de Colisión)
Sea \(M_t = \{H_1, \dots, H_n\} \subset \mathcal{M}_B\) el conjunto de hipótesis activas. Se define el operador de colisión:
\[ \kappa : M_t \times M_t \rightarrow \mathbb{R}_{\ge0} \]
como:
\[ \kappa(H_i,H_j) = \lambda_1\,D_{\mathrm{KL}}(P_i\|P_j) + \lambda_2\,\mathrm{Contr}(H_i,H_j) + \lambda_3\,\mathrm{Overlap}(H_i,H_j) \]
donde:
- \(D_{\mathrm{KL}}\) cuantifica la divergencia informacional.
- \(\mathrm{Contr}\) representa el grado de incompatibilidad lógica, semántica o predictiva.
- \(\mathrm{Overlap}\) mide la redundancia estructural entre ambas hipótesis.
- \(\lambda_k \ge 0\) son parámetros de ponderación del sistema.

Se dice que existe una **colisión activa** cuando \(\kappa(H_i,H_j) > \tau_\kappa\).

---

### Definición 3.2 (Operador de Resolución)
Sea \(\Phi : M_t \times M_t \rightarrow \mathcal{O}\), con \(\mathcal{O} = \{\texttt{merge}, \texttt{branch}, \texttt{evict}, \texttt{isolate}\}\).

Para toda colisión activa (\(\kappa(H_i,H_j) > \tau_\kappa\)), debe existir exactamente una acción \(\Phi(H_i,H_j) \in \mathcal{O}\). La semántica operacional es:
- **merge**: Reemplaza \(\{H_i, H_j\}\) por una hipótesis fusionada.
- **branch**: Mantiene ambas hipótesis mediante bifurcación explícita del estado.
- **evict**: Elimina irreversiblemente una hipótesis de la memoria activa.
- **isolate**: Traslada una hipótesis al archivo frío (\(\mathcal{A}\)).

---

### Axioma 3.1 (Resolución Total)
Todo conflicto detectado debe resolverse inequívocamente:
\[ \forall (H_i,H_j) \in M_t, \quad \kappa(H_i,H_j) > \tau_\kappa \implies \exists! \Phi(H_i,H_j) \]

---

### Definición 3.3 (Dominancia)
Sean \(H_i, H_j \in M_t\). Se dice que \(H_i\) está estrictamente dominada por \(H_j\) si \(p_i u_i \le p_j u_j\) y \(c_i \ge c_j\), con al menos una desigualdad estricta.
En tal caso, \(H_i \prec H_j\). La relación \(\prec\) induce un orden parcial sobre el subespacio activo.

---

### Axioma 3.2 (Evicción Preferente)
Toda hipótesis dominada constituye un candidato preferente para \(\texttt{evict}\) o \(\texttt{isolate}\), excepto cuando su retención garantice el presupuesto inamovible de exploración (\(\epsilon\)), aportando diversidad estructural o cobertura del espacio topológico.

---

### Invariantes del Sistema
Para que la política induzca estabilidad asintótica, el sistema preserva estrictamente:

- **Invariant I (Capacity)**: \( \sum_{i \in M_t} c_i \le B \)
- **Invariant II (Probability Conservation)**: \( \sum_{i \in M_t} p_i = 1 \)
- **Invariant III (Collision Completeness)**: \( \forall (H_i,H_j), \kappa(H_i,H_j) > \tau_\kappa \implies \Phi(H_i,H_j) \) está definida.
- **Invariant IV (Minimum Utility)**: \( \forall H_i \in M_t, \quad p_i u_i \ge \eta \lor H_i \in \mathcal{A} \)
- **Invariant V (Closure)**: \( M_{t+1} = G(M_t, O_t, a_t, a_{\mathrm{mem}}) \in \mathcal{M}_B \)

---

### Proposición 3.1 (Cierre Operacional)
Bajo los invariantes anteriores, toda transición del sistema permanece dentro del espacio factible de memorias acotadas:
\[ M_t \in \mathcal{M}_B \implies M_{t+1} \in \mathcal{M}_B \]

**Esbozo de Demostración:** La actualización secuencial modifica únicamente los pesos probabilísticos \(p_i\). El operador de colisión garantiza que toda incompatibilidad induce una transformación bien definida (Axioma 3.1). Las operaciones \(\Phi\) (fusión, aislamiento, evicción) preservan la restricción de capacidad mediante construcción (Invariant I), mientras que la renormalización explícita mantiene la conservación de masa probabilística (Invariant II). Por tanto, el operador compuesto \(G\) preserva los invariantes de \(\mathcal{M}_B\), concluyendo el cierre.

---

## 4. Programa de Investigación Matemática (Teoremas Objetivo)
La arquitectura RM² abandona su fase de propuesta y se establece como un marco a validar. El objetivo principal es demostrar formalmente la siguiente secuencia matemática:

1. **Lema de Capacidad Fuerte**: Probar que el operador de gestión de memoria \(G\) preserva siempre la restricción dura \(C(M_{t+1}) = \sum_{i} c_i \le B\) bajo cualquier observación \(O_t\), garantizando la inmunidad a desbordamientos térmicos.

2. **Lema de Estabilidad y Ergodicidad**: Demostrar que la política \(\pi\) combinada con \(G\) induce una cadena de Markov sobre \(\mathcal{S} \times \mathcal{M}\) que posee las propiedades de mezclado (mixing conditions) necesarias para garantizar la no-absorción en estados de ignorancia total.

3. **Teorema de Aproximación (Knapsack)**: Bajo los axiomas de independencia y utilidad aditiva, demostrar matemáticamente la optimalidad exacta de la política de evicción basada en \(S_i = \frac{p_i u_i}{c_i}\). Bajo la relajación de estos axiomas, derivar su factor de aproximación respecto a la cota superior del POMDP verdadero.

4. **Teorema de Pérdida por Memoria Finita (Cota Superior Uniforme)**: Establecer una cota superior uniforme para la penalización \(\Delta(B)\) introducida por la restricción física:
   \[ V_B^\pi \ge V_\infty^\pi - \Delta(B) \]
   Donde \(\Delta(B) \rightarrow 0\) conforme \(B \rightarrow \infty\). Esto conecta explícitamente el rendimiento de la inferencia con la teoría de compresión de memoria y el transporte óptimo.

5. **Corolario de Regret Sublineal**: Derivar una cota de *regret* asintótico \(\mathcal{O}(\sqrt{T})\) a partir de los lemas previos y de la garantía de exploración estricta \(\epsilon > 0\), demostrando la convergencia en aprendizaje secuencial bajo capacidad restringida.

---
> **Conclusión**: El olvido agresivo ya no es una decisión narrativa ni termodinámica; es una política de evicción estructural dentro de un POMDP con restricciones duras. Las afirmaciones de RM² están ahora diseñadas para ser demostradas, refutadas y analizadas empíricamente por la literatura de aprendizaje secuencial.
