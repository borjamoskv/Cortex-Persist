import glob
import json
import os

import yaml


def parse_markdown_table(filepath):
    entities = []
    try:
        with open(filepath, encoding='utf-8') as f:
            lines = f.readlines()
            
        in_table = False
        headers = []
        for line in lines:
            line = line.strip()
            if line.startswith('|') and '---' in line:
                continue
            if line.startswith('|'):
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                if not in_table:
                    headers = cells
                    in_table = True
                elif in_table:
                    entity = dict(zip(headers, cells, strict=False))
                    if entity.get('ID'):
                        entities.append(entity)
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
    return entities

def compile_ontology(primitives_dir, output_json, output_yaml):
    print("[C5-REAL] Iniciando Ontology Compiler...")
    
    ontology = {
        'M1_PRIMITIVES': [],
        'M2_INVARIANTS': [],
        'M3_ANTIPATTERNS': [],
        'M4_REDUNDANCIES': [],
        'M5_VECTORS': []
    }
    
    mapping = {
        'MATRIZ_1': 'M1_PRIMITIVES',
        'MATRIZ_2': 'M2_INVARIANTS',
        'MATRIZ_3': 'M3_ANTIPATTERNS',
        'MATRIZ_4': 'M4_REDUNDANCIES',
        'MATRIZ_5': 'M5_VECTORS'
    }
    
    md_files = glob.glob(os.path.join(primitives_dir, "MATRIZ_*_BATCH_*.md"))
    for file in md_files:
        filename = os.path.basename(file)
        for key, target in mapping.items():
            if filename.startswith(key):
                entities = parse_markdown_table(file)
                ontology[target].extend(entities)
    
    for k, v in ontology.items():
        # Sort by ID
        v.sort(key=lambda x: x.get('ID', ''))
        print(f"Compiled {len(v)} entities for {k}")
        
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(ontology, f, indent=2, ensure_ascii=False)
        
    with open(output_yaml, 'w', encoding='utf-8') as f:
        yaml.dump(ontology, f, allow_unicode=True, sort_keys=False)
        
    print(f"[C5-REAL] Ontología cristalizada en JSON y YAML en {primitives_dir}")

if __name__ == '__main__':
    PRIMITIVES_DIR = "cortex/agents/primitives"
    OUTPUT_JSON = os.path.join(PRIMITIVES_DIR, "CORTEX_ONTOLOGY.json")
    OUTPUT_YAML = os.path.join(PRIMITIVES_DIR, "CORTEX_ONTOLOGY.yaml")
    compile_ontology(PRIMITIVES_DIR, OUTPUT_JSON, OUTPUT_YAML)
