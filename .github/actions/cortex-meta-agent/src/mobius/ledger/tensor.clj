(ns mobius.ledger.tensor)

;; ---------------------------------------------------------
;; 1. MÖBIUS LEDGER TENSOR FIELD REPRESENTATION
;; ---------------------------------------------------------
;; El ledger deja de ser cronología; es curvatura en el espacio de mutación.

(def ledger-tensor
  {:dimensions
   {:state-space :ast-latent-manifold
    :operators   [:node-rewrite :subtree-prune :symbol-invert]
    :time        :generations}

   :semantics
   "mutation-pressure-density (how strongly operator o deforms state s at time t)"})

;; ---------------------------------------------------------
;; 2. OPERACIONES TENSORIALES
;; ---------------------------------------------------------

(defn project-pressure
  "Calcula la presión de repulsión acumulada para un estado s y operador o
   a lo largo de todo el eje temporal de generaciones t."
  [ledger current-state operator]
  (let [generations (get ledger current-state)]
    (reduce
      (fn [acc [t ops]]
        (+ acc (get ops operator 0.0)))
      0.0
      generations)))

;; ---------------------------------------------------------
;; 3. GEOMETRÍA DE RIEMANN (Métrica Inducida)
;; ---------------------------------------------------------
;; g_ij(s) = sum_t (L[s, i, t] * L[s, j, t])
;; Define la deformación del espacio de mutaciones inducida por el trauma histórico.

(defn riemann-metric
  "Calcula el componente g_{i,j} de la métrica de Riemann para un estado s.
   Representa la correlación de trauma entre el operador i y el operador j."
  [ledger s op-i op-j]
  (let [generations (get ledger s)]
    (reduce
      (fn [acc [t ops]]
        (let [val-i (get ops op-i 0.0)
              val-j (get ops op-j 0.0)]
          (+ acc (* val-i val-j))))
      0.0
      generations)))

(defn metric-tensor
  "Genera la matriz del tensor métrico g_ij para todos los operadores en un estado dado."
  [ledger s operators]
  (into {}
    (for [i operators]
      [i (into {}
           (for [j operators]
             [j (riemann-metric ledger s i j)]))])))

;; ---------------------------------------------------------
;; 4. EVALUACIÓN GEODÉSICA DE TRAYECTORIA
;; ---------------------------------------------------------

(defn geodesic-drift-cost
  "Calcula el coste de una propuesta de mutación en base a la métrica inducida g_ij.
   Si la trayectoria pasa por un pozo de gravedad de trauma, el coste geodésico se dispara."
  [ledger s operators mutation-vector]
  ;; mutation-vector es un mapa de {operator magnitude}
  (let [g (metric-tensor ledger s operators)]
    (reduce
      (fn [acc [op-i mag-i]]
        (+ acc
           (reduce
             (fn [inner-acc [op-j mag-j]]
               (+ inner-acc (* mag-i mag-j (get-in g [op-i op-j] 0.0))))
             0.0
             mutation-vector)))
      0.0
      mutation-vector)))
