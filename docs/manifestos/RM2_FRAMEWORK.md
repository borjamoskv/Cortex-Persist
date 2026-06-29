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

## 4. Teoremas Fundamentales del Sistema

### Teorema 4.1 (Preservación de Factibilidad)
Sea \(M_t \in \mathcal{M}_B\) una memoria admisible. Si la actualización bayesiana produce probabilidades no negativas, la política satisface el Axioma de Resolución Total (3.1), y la renormalización conserva la masa probabilística, entonces:
\[ M_{t+1} = G(M_t,O_t,a_t,a_{\mathrm{mem}}) \in \mathcal{M}_B \]

**Demostración (Esbozo)**: Las operaciones \(\Phi \in \{\texttt{merge, branch, isolate, evict}\}\) mantienen o reducen el coste total, asegurando \(\sum c_i^{(t+1)} \le B\). La actualización garantiza \(p_i \ge 0\) y la renormalización impone \(\sum p_i = 1\). Toda colisión tiene resolución. Luego los invariantes se preservan \(\implies M_{t+1} \in \mathcal{M}_B\). \(\blacksquare\)

---

### Teorema 4.2 (Terminación Finita de Colisiones)
Sea \(|M_t| < \infty\). Supóngase que cada operación \(\Phi\) reduce estrictamente una medida \(\Psi(M) = \alpha N_c + \beta C + \gamma R\), donde \(N_c\) son colisiones activas, \(C\) el coste excedente y \(R\) la redundancia, con \(\alpha,\beta,\gamma > 0\). Entonces, el proceso de resolución termina en un número finito de pasos.

**Demostración (Esbozo)**: Cada \(\Phi\) disminuye \(\Psi\). Como \(\Psi \ge 0\) y \(M_t\) es finita, no existen cadenas descendentes infinitas. Por el principio del buen orden, la secuencia de resoluciones forzosamente termina. Nunca existen ciclos infinitos resolviendo colisiones. \(\blacksquare\)

---

### Lema 4.1 (Monotonicidad)
Sea \(H_d \in M_t\) una hipótesis estrictamente dominada. Entonces:
\[ V_B^\pi(M_t) \ge V_B^\pi(M_t \setminus \{H_d\}) \]
*Interpretación: Eliminar hipótesis dominadas nunca incrementa artificialmente el valor esperado del sistema.*

---

### Teorema 4.3 (Optimalidad Local)
Si \(H_d\) está dominada por \(H_j\), entonces existe una política \(\pi^*\) tal que:
\[ V_B^{\pi^*} \ge V_B^\pi \]
para cualquier política \(\pi\) que mantenga \(H_d\) en memoria.
*Interpretación: Una política óptima jamás conservaría hipótesis estrictamente dominadas.*

---

### Corolario 4.1 (Expansión de Capacidad)
Sean \(B_1 < B_2\). Entonces \(\mathcal{M}_{B_1} \subseteq \mathcal{M}_{B_2}\).
*Interpretación: A mayor presupuesto de memoria, mayor es el subespacio topológico factible.*

---

### Teorema 4.4 (Convergencia por Función de Lyapunov)
Se define la función de Lyapunov del estado cognitivo:
\[ L(M) = \sum_{i} p_i u_i - \lambda \sum_{i} c_i \]
Si cada acción de gestión de memoria satisface \(L(M_{t+1}) \ge L(M_t)\), entonces \(L\) es una función de Lyapunov válida.
*Interpretación: Garantiza que la política converge a un punto fijo o a un conjunto invariante asintótico, anclando RM² al control óptimo.*

---

## 5. Topología y Métrica del Espacio de Memorias
Para elevar RM² desde un marco axiomático a una teoría con herramientas de análisis funcional, se define formalmente la métrica sobre el espacio de memorias \(\mathcal{M}_B\):

\[ d : \mathcal{M}_B \times \mathcal{M}_B \rightarrow \mathbb{R}_{\ge 0} \]

Definida mediante la distancia compuesta:
\[ d(M_i, M_j) = \alpha\,W(P_i,P_j) + \beta\,|C_i-C_j| + \gamma\,J(M_i,M_j) \]
donde:
- \(W(P_i,P_j)\) es la **Distancia de Wasserstein** entre las distribuciones de probabilidad asociadas a los subgrafos.
- \(|C_i-C_j|\) penaliza la divergencia en el coste de hardware retenido.
- \(J(M_i,M_j)\) es la **Distancia de Jaccard** sobre la topología de los conjuntos de hipótesis activas.

Bajo esta métrica formal, quedan abiertas las pruebas de:
1. **Continuidad** del operador \(G\) respecto a \(d\).
2. **Estabilidad** frente a perturbaciones estocásticas en \(O_t\).
3. **Convergencia global** mediante el Teorema del Punto Fijo de Banach, si el operador \(G\) se demuestra contractivo (\(d(G(x), G(y)) \le k d(x,y)\)).

---

## 6. Tensor de Interacción y Dinámica sobre Grafos Ponderados
Para trascender la heurística escalar de evicción, el espacio \(M_t\) abandona formalmente la noción de "conjunto de hipótesis" y se define como un **grafo topológico ponderado**:
\[ \mathcal{G}_t = (V_t, E_t) \]
Donde los vértices \(V_t\) representan hipótesis individuales y las aristas \(E_t\) codifican relaciones causales, semánticas o de dependencia predictiva.

### El Tensor Completo de Colisiones
El operador \(\kappa\) escalar se generaliza a una matriz o **tensor de interacción**:
\[ \mathbf{K} = (\kappa_{ij})_{i,j} \]
Esta matriz representa el campo de colisiones estructurales de todo el sistema. Las propiedades espectrales de \(\mathbf{K}\) (autovalores, vectores propios, radio espectral \(\rho(\mathbf{K})\)) determinan la estabilidad. Si \(\rho(\mathbf{K})\) aumenta, la memoria acumula conflictos estructurales; si el operador \(\Phi\) logra reducirlo, el sistema estabiliza su topología.

Bajo este formalismo, las acciones de \(\Phi\) adquieren una semántica estricta de teoría de grafos:
- **merge**: Contracción de vértices (Edge Contraction).
- **branch**: Expansión topológica local.
- **evict**: Poda irreversible de subgrafos / eliminación de vértices.
- **isolate**: Partición de grafos (desplazamiento de componentes conexas al archivo frío).

---

## 7. Principios Variacionales de Compresión
La evolución secuencial del agente induce una **trayectoria de memoria**: \(\Gamma = (M_0, M_1, \dots, M_T)\).

### Curvatura de Memoria y Funcional de Acción
Se define la Complejidad Estructural de la memoria como \(C(M) = \alpha |M| + \beta E(M) + \gamma S(M)\), unificando el coste computacional y la entropía topológica (\(S(M) = -\sum p_i \log p_i\)). 

Para optimizar trayectorias completas en lugar de aplicar políticas avariciosas locales, se formula el **Funcional de Acción Cognitiva**:
\[ \mathcal{J}(\Gamma) = \sum_t \left[ V(M_t) - \lambda C(M_t) \right] \]

### Principio Variacional de RM²
El sistema ya no elige solo qué memoria retener, sino que busca la trayectoria global óptima:
\[ \Gamma^* = \arg\max_\Gamma \mathcal{J}(\Gamma) \]
Esto somete la inferencia bajo restricciones de capacidad a ecuaciones análogas a Euler-Lagrange en tiempo discreto.

---
> **Conclusión**: RM² es formalmente una teoría matemática de inferencia sobre grafos bajo restricciones topológicas y termodinámicas. Las intuiciones quedan descartadas; solo el análisis funcional, el control estocástico y el principio de mínima acción rigen la persistencia del estado en CORTEX.
