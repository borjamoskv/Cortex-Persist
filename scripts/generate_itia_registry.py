#!/usr/bin/env python3
import os
import random

# C5-REAL ITIA Registry Generator

DOMAINS = [
    "BFT Semántico (Tolerancia Bizantina de Prompts)",
    "Exergía Computacional (Límites Termodinámicos)",
    "Consenso Causal (Git Sentinel & Ledger)",
    "Sandboxing Mental (Aislamiento de RAM)",
    "Apoptosis Celular (Weaponized Forgetting)",
    "EVI (Expected Value of Information) & Ledger",
    "Colapso de Onda AST (Mutación Determinista)",
    "Incertidumbre Dinámica (Latencia y Red)",
    "Incertidumbre Epistémica (Hipótesis)",
    "Alineación Adversarial (Defensa Estructural)"
]

VERBS_PRI = ["Quema", "Amputa", "Colapsa", "Aísla", "Invalida", "Cifra", "Rechaza", "Purga", "Sobrescribe", "Asesina el hilo de"]
SUBJECTS_PRI = ["el token estocástico", "el vector de incertidumbre", "la ilusión de contexto", "el nodo bizantino", "el teatro de seguridad", "la alucinación latente", "la conjetura LLM", "el green theater", "la entropía semántica", "el ruido de inferencia"]
CONDITIONS_PRI = ["si Δ_exergia == 0.", "bajo umbral de consenso BFT.", "antes de la mutación en WAL.", "tras fallo de validación empírica.", "si carece de firma Ed25519.", "en la RAM efímera (OOM simulado).", "en la fase SAGA-1.", "si el ROI_surprise es negativo.", "al detectar divergencia en el Swarm.", "sin requerir confirmación del Operador."]

VERBS_INV = ["PROHIBIDO:", "MANDATORIO:", "RECHAZO ABSOLUTO:", "NULO:", "EXIGENCIA:"]
SUBJECTS_INV = ["La inferencia pasiva", "El almacenamiento de strings sueltas", "La conjetura sin hash", "El bucle analítico infinito", "La diplomacia en el log", "La escritura cruzada de tenants", "La ejecución bloqueante IO", "La recomputación de prefijos", "El estado probabilístico persistente", "La delegación sin TTFT estricto"]
CONDITIONS_INV = ["se considera Anergía P0.", "se castiga con Apoptosis inmediata.", "provoca Git Rollback atómico.", "invalida el Ledger criptográfico.", "requiere justificación YAML estricta.", "drena exergía y aborta SAGA.", "fuerza un colapso de estado a cero.", "viola la Ley de Landauer.", "implica contaminación de la ontología.", "es una violación del motor causal base 60."]

ANTI_PATTERNS = [
    "Usar try-except sin logging del hash causante.",
    "Esperar a la latencia web sin un Timeout determinista.",
    "Aceptar código sin verificar el AST parsing.",
    "Crear artefactos sin declarar el Autor (Demiurgo).",
    "Usar prosa para explicar un error en vez de mutar el estado.",
    "Ejecutar un sub-agente sin calcular el EVI previo.",
    "Mantener el contexto de un error después de resolverlo.",
    "Responder 'Lo haré' en lugar de ejecutar un commit."
]

REDUNDANCIES = [
    "Doble Hash (SHA-256 en Ledger, SHA3-256 en Taint).",
    "Quorum Mínimo N=3 para aserciones de estado crítico.",
    "Timeouts asíncronos y Watchdogs de event-loop independientes.",
    "Copias de seguridad transaccionales (SAGA Snapshot) previas a la escritura.",
    "Validación cruzada de LLMs (Opus para arquitectura, Flash para ruteo)."
]

def generate_registry():
    content = ["<!-- [C5-REAL] Exergy-Maximized -->\n# ITIA_REGISTRY: 100 Primitivas y 100 Invariantes\n\n> **\"La Tolerancia a la Incertidumbre no es fe; es criptografía y termodinámica.\"**\n\n"]
    
    pri_counter = 1
    inv_counter = 1
    
    random.seed(42) # Determinismo
    
    for i, domain in enumerate(DOMAINS):
        content.append(f"## Dominio {i+1}: {domain}\n")
        
        # 10 Primitivas
        content.append("### Primitivas de Colapso (Mecanismos)\n")
        for _ in range(10):
            verb = random.choice(VERBS_PRI)
            subj = random.choice(SUBJECTS_PRI)
            cond = random.choice(CONDITIONS_PRI)
            content.append(f"- **ITIA-PRI-{pri_counter:03d}**: {verb} {subj} {cond}\n")
            pri_counter += 1
            
        # 10 Invariantes
        content.append("\n### Invariantes (Reglas Termodinámicas)\n")
        for _ in range(10):
            verb = random.choice(VERBS_INV)
            subj = random.choice(SUBJECTS_INV)
            cond = random.choice(CONDITIONS_INV)
            content.append(f"- **ITIA-INV-{inv_counter:03d}**: **{verb}** {subj} {cond}\n")
            inv_counter += 1
            
        # 2 Anti-patrones
        content.append("\n### Antipatrones Detectados\n")
        ants = random.sample(ANTI_PATTERNS, 2)
        for ant in ants:
            content.append(f"- ❌ {ant}\n")
            
        # 1 Redundancia
        content.append("\n### Redundancia Activa (Mitigación C5)\n")
        red = random.choice(REDUNDANCIES)
        content.append(f"- 🛡️ {red}\n\n")
        content.append("---\n")
        
    # Escribir el archivo
    output_path = "docs/manifestos/ITIA_REGISTRY.md"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.writelines(content)
        
    print(f"Generated {pri_counter-1} Primitives and {inv_counter-1} Invariants at {output_path}")

if __name__ == "__main__":
    generate_registry()
