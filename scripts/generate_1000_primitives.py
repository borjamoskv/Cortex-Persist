import json
import itertools
from pathlib import Path

# The 10 Fundamental Theories
THEORIES = {
    "CAT": {"name": "Teoría de Categorías", "constraint": "Isomorfismo Estructural", "anti_pattern": "Mapeo con Pérdida", "mechanism": "Functores Estrictos"},
    "THD": {"name": "Termodinámica de Computación", "constraint": "Cero Anergía", "anti_pattern": "Bucle Disipativo", "mechanism": "Límite de Landauer"},
    "CAU": {"name": "Inferencia Causal (Do-Calculus)", "constraint": "Intervención Determinista", "anti_pattern": "Correlación Espuria", "mechanism": "Operador Do(x)"},
    "TYP": {"name": "Teoría de Tipos Homotópicos", "constraint": "Habitabilidad de Prueba", "anti_pattern": "Afirmación sin Compilación", "mechanism": "Isomorfismo Curry-Howard"},
    "BFT": {"name": "Tolerancia Bizantina", "constraint": "Consenso N>2/3", "anti_pattern": "Validación Sybil", "mechanism": "Quorum Mayoritario"},
    "CYB": {"name": "Cibernética de Control", "constraint": "Homeostasis de Estado", "anti_pattern": "Divergencia Silenciosa", "mechanism": "Feedback Negativo"},
    "TOP": {"name": "Topología Algebraica", "constraint": "Preservación de Vecindad", "anti_pattern": "Fractura Vectorial", "mechanism": "Cálculo de Homología"},
    "CPX": {"name": "Complejidad Computacional", "constraint": "Cota Polinomial Estricta", "anti_pattern": "Fuerza Bruta NP-Hard", "mechanism": "Reducción Oracular"},
    "DYN": {"name": "Sistemas Dinámicos", "constraint": "Convergencia a Atractor", "anti_pattern": "Caos Determinista", "mechanism": "Control de Exponente de Lyapunov"},
    "INF": {"name": "Teoría de Información", "constraint": "Densidad de Exergía Máxima", "anti_pattern": "Ruido de Canal / Slop", "mechanism": "Compresión Entrópica"}
}

# 10 Operations
OPERATIONS = {
    "MAP": "Mapeo",
    "RED": "Reducción",
    "ISO": "Aislamiento",
    "COM": "Composición",
    "PRV": "Preservación",
    "TRN": "Transformación",
    "LIM": "Acotamiento",
    "SYN": "Sincronización",
    "VAL": "Validación",
    "COL": "Colapso"
}

# 10 Targets
TARGETS = {
    "AST": "Árbol de Sintaxis Abstracta",
    "MEM": "Memoria Persistente (SQLite)",
    "CTX": "Ventana de Contexto",
    "VEC": "Espacio Vectorial",
    "THR": "Hilo de Ejecución",
    "SWR": "Enjambre de Agentes",
    "LED": "Ledger Criptográfico",
    "PRM": "Prompt / Inyección Causal",
    "DOM": "Grafo DOM / Interfaz",
    "NET": "Topología de Red"
}

primitives = []
primitive_idx = 1

for t_code, t_data in THEORIES.items():
    for op_code, op_name in OPERATIONS.items():
        for tgt_code, tgt_name in TARGETS.items():
            prim_id = f"PRIM-{t_code}-{op_code}-{tgt_code}"
            
            # Semantic Assembly
            name = f"{op_name} de {tgt_name} ({t_data['name']})"
            desc = f"Invariante estructural que aplica {op_name.lower()} sobre {tgt_name} garantizando {t_data['constraint']}."
            rule = f"Rechazar {t_data['anti_pattern']} mediante {t_data['mechanism']}."
            
            primitives.append({
                "id": prim_id,
                "global_index": primitive_idx,
                "theory": t_data["name"],
                "operation": op_name,
                "target": tgt_name,
                "name": name,
                "description": desc,
                "c5_rule": rule
            })
            primitive_idx += 1

# Write JSON
out_dir = Path("babylon60/agents/primitives")
out_dir.mkdir(parents=True, exist_ok=True)

json_path = out_dir / "ONTOLOGIA_1000_PRIMITIVAS.json"
md_path = out_dir / "ONTOLOGIA_1000_PRIMITIVAS.md"

with open(json_path, "w", encoding="utf-8") as f:
    json.dump({"primitives": primitives}, f, indent=2, ensure_ascii=False)

# Write MD
with open(md_path, "w", encoding="utf-8") as f:
    f.write("<!-- [C5-REAL] Exergy-Maximized -->\n")
    f.write("# 🌌 ONTOLOGÍA C5-REAL: 1000 PRIMITIVAS ESTRUCTURALES\n\n")
    f.write("> **Generado Autónomamente (AUTODIDACT-OMEGA)**\n")
    f.write("> Isomorfismo Combinatorio: 10 Teorías × 10 Operadores × 10 Objetivos = 1000 Invariantes.\n")
    f.write("> SYS_ID: borjamoskv\n\n")
    
    current_theory = ""
    for p in primitives:
        if p["theory"] != current_theory:
            current_theory = p["theory"]
            f.write(f"\n## 🔴 {current_theory}\n\n")
        
        f.write(f"### `{p['id']}` - {p['name']}\n")
        f.write(f"- **Descripción:** {p['description']}\n")
        f.write(f"- **Directiva C5:** {p['c5_rule']}\n\n")

print(f"Generated {len(primitives)} primitives.")
print(f"JSON path: {json_path}")
print(f"MD path: {md_path}")
