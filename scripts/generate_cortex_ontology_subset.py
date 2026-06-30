# scripts/generate_cortex_ontology_subset.py
# [C5-REAL] Exergy-Maximized

import os
import re

def parse_table_rows(file_path: str, prefix: str, limit: int) -> list:
    if not os.path.exists(file_path):
        print(f"Error: {file_path} no encontrado.")
        return []
        
    rows = []
    headers = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("|"):
                parts = [p.strip() for p in stripped.split("|")[1:-1]]
                if not parts:
                    continue
                # Omitir separadores de tabla
                if all(re.match(r"^:?-+:?$", p) for p in parts):
                    continue
                # Si el primer campo coincide con el header de ID
                if parts[0] == "ID":
                    headers = parts
                    continue
                # Detectar ID del patrón (ej: P-001, AP-001, I-001)
                clean_id = re.sub(r"[\*\s]", "", parts[0])
                if clean_id.startswith(prefix):
                    rows.append(parts)
                    if len(rows) == limit:
                        break
    return {"headers": headers, "rows": rows}

def main():
    base_dir = "babylon60/agents/primitives"
    out_file = os.path.join(base_dir, "ONTOLOGIA_CONSOLIDADA.md")
    
    # 1. 100 Primitivas
    p_data = parse_table_rows(os.path.join(base_dir, "MATRIX_1_PRIMITIVAS.md"), "P-", 100)
    # 2. 100 Invariantes
    i_data = parse_table_rows(os.path.join(base_dir, "MATRIX_2_INVARIANTES.md"), "I-", 100)
    # 3. 20 Antipatrones
    ap_data = parse_table_rows(os.path.join(base_dir, "MATRIX_3_4_5_ANTIPATRONES_REDUNDANCIAS_ADVERSARIAL.md"), "AP-", 20)
    # 4. 10 Redundancias
    r_data = parse_table_rows(os.path.join(base_dir, "MATRIX_3_4_5_ANTIPATRONES_REDUNDANCIAS_ADVERSARIAL.md"), "R-", 10)
    # 5. 50 Vectores Adversariales
    v_data = parse_table_rows(os.path.join(base_dir, "MATRIX_3_4_5_ANTIPATRONES_REDUNDANCIAS_ADVERSARIAL.md"), "V-", 50)
    
    with open(out_file, "w", encoding="utf-8") as out:
        out.write("# ONTOLOGIA CONSOLIDADA C5-REAL\n\n")
        out.write("> **SYS_ID:** borjamoskv\n")
        out.write("> **Nivel de Realidad:** C5-REAL\n")
        out.write("> *Este documento es el consolidado verificado de entidades ontológicas de CORTEX-Persist.*\n\n")
        
        # Escribir Primitivas
        out.write("## 1. 100 Primitivas de Colapso (prims)\n\n")
        out.write("| " + " | ".join(p_data["headers"]) + " |\n")
        out.write("| " + " | ".join([":---" for _ in p_data["headers"]]) + " |\n")
        for row in p_data["rows"]:
            out.write("| " + " | ".join(row) + " |\n")
        out.write("\n\n")
        
        # Escribir Invariantes
        out.write("## 2. 100 Invariantes Confirmados (invt)\n\n")
        out.write("| " + " | ".join(i_data["headers"]) + " |\n")
        out.write("| " + " | ".join([":---" for _ in i_data["headers"]]) + " |\n")
        for row in i_data["rows"]:
            out.write("| " + " | ".join(row) + " |\n")
        out.write("\n\n")
        
        # Escribir Antipatrones
        out.write("## 3. 20 Antipatrones Purgados (antip)\n\n")
        out.write("| " + " | ".join(ap_data["headers"]) + " |\n")
        out.write("| " + " | ".join([":---" for _ in ap_data["headers"]]) + " |\n")
        for row in ap_data["rows"]:
            out.write("| " + " | ".join(row) + " |\n")
        out.write("\n\n")
        
        # Escribir Redundancias
        out.write("## 4. 10 Redundancias Eliminadas/Activas (redun)\n\n")
        out.write("| " + " | ".join(r_data["headers"]) + " |\n")
        out.write("| " + " | ".join([":---" for _ in r_data["headers"]]) + " |\n")
        for row in r_data["rows"]:
            out.write("| " + " | ".join(row) + " |\n")
        out.write("\n\n")
        
        # Escribir Vectores Adversariales
        out.write("## 5. 50 Vectores Adversariales (Red Teaming)\n\n")
        out.write("| " + " | ".join(v_data["headers"]) + " |\n")
        out.write("| " + " | ".join([":---" for _ in v_data["headers"]]) + " |\n")
        for row in v_data["rows"]:
            out.write("| " + " | ".join(row) + " |\n")
        out.write("\n")
        
    print(f"ÉXITO: Reporte de ontología consolidada generado en {out_file}.")

if __name__ == "__main__":
    main()
