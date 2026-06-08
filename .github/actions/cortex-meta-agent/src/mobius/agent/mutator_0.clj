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

(defn generate-synthetic-countersamples
  "Genera ejemplos sintéticos de mutaciones fallidas para inyectar presión negativa
   antes de que el agente gaste cómputo explorando zonas muertas."
  [baseline-ast]
  ;; Por ahora emulamos la generación de 2 anti-patrones estructurales.
  [{:pattern :infinite-recursion-trap :reason "Generates unchecked StackOverflow"}
   {:pattern :state-pollution-trap :reason "Violates C4-SIM shadow isolation"}])

(defn extract-mutation-vector
  "Extrae el tensor de presión dual:
   1. positive-pressure: direccionalidad basada en historial de fracasos reales.
   2. negative-pressure: antiejemplos sintéticos para podar el espacio de búsqueda latente."
  [ledger-history baseline-ast]
  (let [rejections (filter #(not (:promoted? %)) ledger-history)
        reasons (frequencies (map :rejection-reason rejections))
        target (if (> (get reasons :complexity-growth-exceeded 0)
                      (get reasons :tests-failed 0))
                 :subtree-prune
                 :node-rewrite)]
    {:positive-pressure {:rejection-history reasons
                         :mutation-target target}
     :negative-pressure (generate-synthetic-countersamples baseline-ast)}))

(defn apply-pressure-field
  "Genera un candidato aplicando el tensor dual histórico/sintético."
  [baseline-ast ledger-history]
  (let [tensor (extract-mutation-vector ledger-history baseline-ast)]
    ;; El LLM recibe tanto los errores pasados (positive-pressure) como
    ;; los campos minados teóricos (negative-pressure).
    {:candidate-ast '... ;; (AST deformado por el LLM bajo presión dual)
     :applied-tensor tensor}))
