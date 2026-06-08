(ns mobius.agent.mutator-0
  (:require [mobius.fitness.shadow :as shadow]
            [mobius.fitness.ast :as ast]))

;; ---------------------------------------------------------
;; MUTATOR-0: Semilla de Presión Evolutiva
;; ---------------------------------------------------------
;; No es un pipeline, es una fuerza de deformación local.

(def mutator-config
  {:agent/id :mutator-0
   :mode :pressure-field

   :mutation-policy
   {:target-space [:ast :fitness-landscape]
    :operations [:node-rewrite :subtree-prune :symbol-invert]
    :constraints {:max-depth-delta 2
                  :forbidden-paths ["mobius.fitness/*"
                                    "mobius.eval/*"
                                    "ledger/*"]}}

   :selection-bias
   {:type :entropy-weighted
    :pressure-function :loss-gradient-plus-diversity-drift}

   :reproduction-rule
   {:survive-if [:fitness-improves :novelty-increases]
    :die-if :stagnation-3-generations}})

;; ---------------------------------------------------------
;; BIFURCACIÓN 3: LEDGER INVERSION (Anamnesis Evolutiva)
;; ---------------------------------------------------------
;; El historial de fracasos no es auditoría, es el vector de
;; mutación que condiciona el campo de presión.

(defn extract-mutation-vector
  "Extrae el vector de presión de las últimas N mutaciones rechazadas."
  [ledger-history]
  (let [rejections (filter #(not (:promoted? %)) ledger-history)
        reasons (frequencies (map :rejection-reason rejections))]
    {:pressure-bias reasons
     :mutation-target (if (> (get reasons :complexity-growth-exceeded 0)
                             (get reasons :tests-failed 0))
                        :subtree-prune
                        :node-rewrite)}))

(defn apply-pressure-field
  "Genera un candidato aplicando el vector histórico sobre el baseline."
  [baseline-ast ledger-history]
  (let [vector (extract-mutation-vector ledger-history)]
    ;; Aquí se delegaría al LLM inyectando el `vector` en el system prompt
    ;; para forzar la deformación en la dirección contraria al fracaso acumulado.
    {:candidate-ast '... ;; (AST deformado por el LLM)
     :applied-pressure vector}))
