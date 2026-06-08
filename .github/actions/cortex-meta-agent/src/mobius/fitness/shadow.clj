(ns mobius.fitness.shadow
  (:require [mobius.fitness.ast :as ast]))

;; ---------------------------------------------------------
;; 1. AISLAMIENTO C4-SIM (SHADOW CONTEXT)
;; ---------------------------------------------------------

(def ^:dynamic *shadow-mode* false)
(def ^:dynamic *shadow-events* (atom []))

(defmacro with-shadow-context
  "Ejecuta `body` en modo shadow interceptando side-effects.
   Cualquier operación externa debe leer `*shadow-mode*` y, si es true,
   hacer (swap! *shadow-events* conj {:event :suppressed-side-effect ...})
   en lugar de mutar el estado."
  [& body]
  `(binding [*shadow-mode* true
             *shadow-events* (atom [])]
     (let [start# (System/nanoTime)
           result# (try
                     ~@body
                     (catch Exception e#
                       {:error (ex-message e#)}))
           latency-ms# (/ (double (- (System/nanoTime) start#)) 1000000.0)]
       {:result result#
        :latency-ms latency-ms#
        :side-effects @*shadow-events*})))


;; ---------------------------------------------------------
;; 2. SHADOW EVALUATOR
;; ---------------------------------------------------------

(defn evaluate-candidate
  "Ejecuta una función en modo shadow midiendo latencia y validación causal."
  [f input ctx]
  (with-shadow-context
    (f input ctx)))

(defn shadow-eval
  "Ejecuta M y M' con el mismo input y contexto, comparando fitness y aplicando
   las restricciones de promoción."
  [{:keys [mutation-id baseline candidate input ctx candidate-ast e-tokens-spent]}]

  (let [baseline-eval (evaluate-candidate baseline input ctx)
        candidate-eval (evaluate-candidate candidate input ctx)

        ;; Validación causal básica (si candidate devolvió un error, w-causal = 0)
        baseline-causal (if (:error (:result baseline-eval)) 0 1)
        candidate-causal (if (:error (:result candidate-eval)) 0 1)

        ;; Cálculos AST (asumimos que la métrica de complejidad se pre-calculó o se inyecta)
        ;; Si no hay AST de candidate, asumimos penalización.
        c-ast (if candidate-ast (ast/complexity candidate-ast 'candidate-fn) 10.0)

        ;; Generar métricas emuladas para el candidato
        candidate-metrics {:w-causal candidate-causal
                           :w-speed (if (zero? (:latency-ms baseline-eval))
                                        1.0
                                        (/ (:latency-ms baseline-eval) (:latency-ms candidate-eval)))
                           :c-ast c-ast
                           :e-tokens (or e-tokens-spent 0)
                           :r-stability 1.0} ;; Estabilidad = 1.0 en test único, requiere N corridas para desviación.

        baseline-metrics {:w-causal baseline-causal
                          :w-speed 1.0
                          :c-ast (if candidate-ast (ast/complexity candidate-ast 'baseline-fn) 10.0)
                          :e-tokens 0
                          :r-stability 1.0}

        baseline-score (ast/fitness-score baseline-metrics)
        candidate-score (ast/fitness-score candidate-metrics)

        fitness-delta (- candidate-score baseline-score)

        ;; Criterios de Promoción
        min-fitness-delta 0.15
        max-latency-regression 0.0
        max-complexity-growth 1.20

        tests-pass? (= candidate-causal 1)
        fitness-ok? (>= fitness-delta min-fitness-delta)
        latency-ok? (<= (:latency-ms candidate-eval) (:latency-ms baseline-eval))
        complexity-ok? (<= (:c-ast candidate-metrics) (* (:c-ast baseline-metrics) max-complexity-growth))

        promoted? (and tests-pass? fitness-ok? latency-ok? complexity-ok?)

        rejection-reason (cond
                           (not tests-pass?) :tests-failed
                           (not complexity-ok?) :complexity-growth-exceeded
                           (not latency-ok?) :latency-regression
                           (not fitness-ok?) :insufficient-fitness-delta
                           :else nil)]

    {:mutation-id mutation-id
     :status :evaluated
     :timestamp (System/currentTimeMillis)

     :baseline-result (:result baseline-eval)
     :candidate-result (:result candidate-eval)

     :baseline-metrics (assoc baseline-metrics :latency-ms (:latency-ms baseline-eval))
     :candidate-metrics (assoc candidate-metrics :latency-ms (:latency-ms candidate-eval))

     :baseline-score baseline-score
     :candidate-score candidate-score
     :fitness-delta fitness-delta

     :promotion-criteria {:tests-pass tests-pass?
                          :fitness-ok fitness-ok?
                          :latency-ok latency-ok?
                          :complexity-ok complexity-ok?}

     :promoted? promoted?
     :rejection-reason rejection-reason}))


;; ---------------------------------------------------------
;; 3. EVOLUTION LEDGER
;; ---------------------------------------------------------

(def evolution-ledger (atom []))

(defn record-evolution-ledger!
  "Guarda el resultado de una evaluación en el ledger de MÖBIUS."
  [eval-result]
  (swap! evolution-ledger conj eval-result)
  ;; En C5-REAL, esto escribiría a un archivo .jsonl o base de datos local
  eval-result)

(defn run-and-record-shadow!
  "Corre el shadow eval y cristaliza el resultado."
  [params]
  (-> (shadow-eval params)
      (record-evolution-ledger!)))
