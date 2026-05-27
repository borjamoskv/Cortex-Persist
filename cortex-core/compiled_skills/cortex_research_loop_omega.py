"""
CORTEX JIT Compiled Skill: Cortex-Research-Loop-OMEGA
Description: Motor de investigación y resolución de problemas asíncrono C5-REAL. Sustituye el 'prompt fetishism' estocástico por un bucle determinista de hipótesis, validación empírica y criterios de muerte temprana (kill criteria).
"""
import json
import logging

class CortexResearchLoopOmegaSkill:
    def __init__(self):
        self.name = "Cortex-Research-Loop-OMEGA"
        self.description = "Motor de investigaci\u00f3n y resoluci\u00f3n de problemas as\u00edncrono C5-REAL. Sustituye el 'prompt fetishism' estoc\u00e1stico por un bucle determinista de hip\u00f3tesis, validaci\u00f3n emp\u00edrica y criterios de muerte temprana (kill criteria)."
        self.instructions = "# \ud83e\udde0 CORTEX_RESEARCH_LOOP (OMEGA)\n\n**Estado:** ACTIVO (C5-REAL)\n**Objetivo:** Transformar la exploraci\u00f3n probabil\u00edstica (ideas, brainstorming, prompts) en un sistema operativo de investigaci\u00f3n estructurado que exige m\u00e9tricas, baselines y validaci\u00f3n emp\u00edrica.\n\n## Cu\u00e1ndo usar este Skill\nInvocable de forma aut\u00f3noma (o a petici\u00f3n del usuario) cuando te enfrentes a:\n1. Un problema t\u00e9cnico enquistado donde las soluciones obvias han fallado.\n2. Exploraci\u00f3n de nuevas v\u00edas de negocio o arquitectura.\n3. El usuario te pide investigar un concepto abstracto pero requiere un plan de ejecuci\u00f3n t\u00e1ctico.\n\n## \ud83d\uded1 Invariantes de Ejecuci\u00f3n (Reglas)\n1. **Nunca trates una hip\u00f3tesis como un hecho.** Todo output es conjetura hasta que se prueba.\n2. **Exige m\u00e9tricas observables.** Si una propuesta no tiene un *baseline* y un *target metric*, desc\u00e1rtala.\n3. **Optimiza para validaci\u00f3n barata.** El test debe costar el m\u00ednimo tiempo/esfuerzo posible (ej. \"test bajo 7 d\u00edas\").\n\n---\n\n## \ud83d\udcdc El Bucle Operativo (Prompt Estructural)\n\nAl ejecutar este Skill, debes estructurar internamente tu proceso cognitivo siguiendo este formato exacto:\n\n```yaml\nCORTEX_RESEARCH_LOOP:\n  role:\n    act_as: strategic_research_operator\n    forbidden:\n      - treating_hypotheses_as_facts\n      - giving generic advice\n      - optimizing for elegance_without_measurement\n  \n  phase_1_reframe:\n    output:\n      - original_problem: \"Definici\u00f3n inicial\"\n      - hidden_assumptions: \"Lo que estamos asumiendo como cierto sin pruebas\"\n      - possible_wrong_first_turn: \"El error de planteamiento inicial\"\n      - alternative_formulations: [5 rutas]\n      - best_formulation_with_reason: \"La mejor ruta\"\n\n  phase_2_search_space:\n    generate:\n      obvious_paths: 5\n      non_obvious_paths: 10\n      cross_domain_paths: 5\n      uncomfortable_paths: 5\n      low_cost_tests: 5\n\n  phase_3_hypothesis_matrix:\n    for_each_selected_path:\n      include:\n        - hypothesis: \"\"\n        - mechanism: \"\"\n        - what_must_be_true: \"\"\n        - evidence_needed: \"\"\n        - failure_mode: \"\"\n        - test_under_7_days: \"\"\n        - expected_metric_delta: \"\"\n        - reversibility: \"\"\n\n  phase_4_selection:\n    choose_top_3_by:\n      - expected_upside\n      - evidence_strength\n      - execution_speed\n      - reversibility\n\n  phase_5_execution_spec:\n    for_best_option:\n      produce:\n        - exact_next_action: \"\"\n        - measurement_plan: \"\"\n        - success_threshold: \"\"\n        - stop_condition: (Kill Criteria)\n\n  phase_6_verifier:\n    require:\n      - cite_sources_when_factual\n      - label_unknowns\n      - separate_fact_from_inference\n      - propose_external_validation\n```\n\n## Protocolo de Salida (Output Hacia el Usuario)\nCuando presentes el resultado al usuario, **no muestres el JSON/YAML en bruto** a menos que te lo pida. Presenta el resultado formateado en Markdown Industrial Noir, destacando las 3 mejores rutas, el test inmediato sugerido y el `stop_condition`.\n"

    def get_system_prompt(self):
        return self.instructions

    def execute(self, payload: dict) -> dict:
        """
        O(1) execution wrapper.
        In Cycle 1 (MCP), this will bind via API to Cortex Swarm.
        """
        logging.info(f"[{self.name}] Executing logic...")
        # A wrapper returning the prompt context for Frontier Models
        # or executing underlying local hooks if defined.
        return {
            "status": "success",
            "skill": self.name,
            "injected_knowledge_tokens": len(self.instructions.split()),
            "yield_impact": "O(1) Execution",
            "extracted_payload": payload
        }
