"""
CORTEX JIT Compiled Skill: Estado-Del-Arte-OMEGA
Description: Motor determinista C5-REAL para síntesis del Estado del Arte (SOTA). Ejecuta el SOTA-Loop estructurado en 4 fases aniquilando el ruido teórico.
"""
import json
import logging

class EstadoDelArteOmegaSkill:
    def __init__(self):
        self.name = "Estado-Del-Arte-OMEGA"
        self.description = "Motor determinista C5-REAL para s\u00edntesis del Estado del Arte (SOTA). Ejecuta el SOTA-Loop estructurado en 4 fases aniquilando el ruido te\u00f3rico."
        self.instructions = "# Estado-Del-Arte-OMEGA v1.0.0\n\nSkill generada v\u00eda SORTU-APEX JIT Compiler a partir del `Guia estados del arte` (G\u00f3mez Vargas et al.) y la heur\u00edstica de repositorios Best Papers.\n\n## 1. Topolog\u00eda del Concepto\nEl **Estado del Arte** es una metodolog\u00eda de investigaci\u00f3n cualitativo-documental de car\u00e1cter cr\u00edtico-interpretativo.\n**Invariante:** *No es el Marco Te\u00f3rico*. \n- **Marco Te\u00f3rico:** Definici\u00f3n y organizaci\u00f3n est\u00e1tica de abstracciones.\n- **Estado del Arte:** Evaluaci\u00f3n emp\u00edrica de resultados recientes (\u00faltimos 10 a\u00f1os o 2-3 para IA/CS) para identificar el *vac\u00edo ex\u00e9rgico*.\n\n## 2. Vectores de Extracci\u00f3n (Best Papers)\nPara evitar reinventar la rueda, la extracci\u00f3n es jer\u00e1rquica:\n- **AI & CS:** *Best Papers Awards in Computer Science* (Brown Univ) y ML conferences (NeurIPS, ICML).\n- **Hardware & Eng:** *IEEE Computer Society Best Paper Awards*.\n- **Multidisciplinar:** *Google Scholar* metric index (optimizaci\u00f3n por citas).\n\n## 3. SOTA-Loop (El Bucle de Forja)\nEl motor de s\u00edntesis ejecuta este pipeline O(1):\n1. **Delimitaci\u00f3n Temporal:** 2-3 a\u00f1os para campos din\u00e1micos; hasta 10 a\u00f1os para est\u00e1ticos. B\u00fasqueda en Scopus/WoS/Dialnet.\n2. **Matriz Anal\u00edtica:** Estructuraci\u00f3n inmutable: `[Autor | A\u00f1o | Objetivos | Metodolog\u00eda | Resultados | Conclusiones]`.\n3. **Biopsia Cr\u00edtica:** Extracci\u00f3n del mecanismo base y el fallo estructural (limitaci\u00f3n).\n4. **Cristalizaci\u00f3n:** Redacci\u00f3n *Zero-Rhetoric* que vincula posturas y expone qu\u00e9 falta por resolver.\n\n## Invariantes\n- **C5-REAL:** Sin matriz anal\u00edtica verificable y posicionamiento cr\u00edtico frente a errores pasados, no se acepta el documento como SOTA.\n- **GITHUB-SOTA-MANDATE:** Si se alcanza el \"Estado del Arte\" (SOTA) en cualquier disciplina, componente o proyecto, **SIEMPRE** tiene que estar demostrado emp\u00edricamente y reflejado/commiteado en GitHub. La excelencia no subida a GitHub es inexistente.\n- **ANTI-SURVEY MANDATE:** Ignorar cualquier paper que no proponga un cambio estructural. Los \"Survey Papers\" se usan solo para extraer bibliograf\u00eda, nunca como fuente primaria.\n"

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
