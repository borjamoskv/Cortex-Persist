import hashlib
import json
from pathlib import Path

THEORIES = {
    "CAT": {"name": "Teoría de Categorías", "substrate": "Morfismos/Functores"},
    "THD": {"name": "Termodinámica de la Computación", "substrate": "Exergía/Entropía"},
    "CAU": {"name": "Inferencia Causal Estructural", "substrate": "Grafos DAG/Intervenciones"},
    "TYP": {"name": "Teoría de Tipos Homotópicos", "substrate": "Tipos/Pruebas"},
    "BFT": {"name": "Tolerancia Bizantina / Diseño de Mecanismos", "substrate": "Consenso/Quorum"},
    "CYB": {"name": "Cibernética de Segundo Orden", "substrate": "Feedback/Homeostasis"},
    "TOP": {"name": "Topología Algebraica / Grafos Complejos", "substrate": "Nodos/Homología"},
    "CPX": {"name": "Complejidad Computacional", "substrate": "Recursos/Oráculos"},
    "DYN": {"name": "Sistemas Dinámicos / Caos", "substrate": "Atractores/Fases"},
    "INF": {"name": "Física de la Información", "substrate": "Bits/Canales"}
}

BASE_PRIMITIVES = {
    "CAT": ["Functor de preservación de estado", "Transformación natural", "Límite / colímite", "Isomorfismo", "Adjunción", "Mónada", "Yoneda Embedding", "Equivalencia de Categorías", "Topos", "Kan Extension", "Producto Fibrado", "Composición Asociativa"],
    "THD": ["Límite de Landauer", "Exergía computacional disponible", "Disipación estocástica", "Reversibilidad Condicional", "Costo de Copia vs Borrado", "Entalpía de Representación", "Balance de Exergía", "Umbral de Disipación Crítica", "Transducción de Información a Energía", "Amortiguación Termodinámica", "Contabilidad de Exergía en Swarm", "Ley de No-Creación de Exergía"],
    "CAU": ["Operador do(x) (intervención)", "Colisionador causal", "D-separación", "Identificación Causal", "Gráfico Causal Mínimo", "Contrafactuales Estructurales", "Ajuste de Backdoor", "Frontera de Ignorabilidad", "Intervención en Grafos Dinámicos", "Transporte Causal", "Mediación y Moderación", "Robustez a Incertidumbre de Modelo"],
    "TYP": ["Tipo dependiente", "Identidad proposicional", "Habitabilidad de tipo", "Path-type de equivalencia", "Higher-inductive constructor", "Truncación n-tipo", "Eliminador de unicornio", "Gluing lemma", "Modalidad de necesidad", "Universo jerárquico", "Isomorfismo Curry-Howard", "Univalence Axiom"],
    "BFT": ["Quorum mayoritario", "Sybil forzado", "Equilibrio de Nash asimétrico", "Commit-reveal aleatorizado", "Slashing de confianza", "Votación ponderada", "Gossip anti-eclipse", "Umbral f < n/3", "Timeout adaptativo", "Fair-ordering mempool", "Prueba de Trabajo / Participación", "Firma Múltiple BFT"],
    "CYB": ["Bucle de retroalimentación negativa", "Observabilidad del estado", "Histéresis cognitiva", "Ganancia homeostática variable", "Meta-control", "Buffer antiflaping", "Latencia de percepción", "Ajuste punto-de-referencia", "Inercia de mando", "Reflexividad recursiva", "Autopoiesis Estructural", "Variedad Requerida de Ashby"],
    "TOP": ["Número de Betti", "Isomorfismo de subgrafos", "Centralidad de autovector", "Homología persistente", "Filtro de comunidad Louvain", "Walk-entropy descriptor", "Puente de Cheeger", "Contractibilidad parcial", "Curvatura de Ollivier-Ricci", "Retráctil de núcleo", "Complejo Simplicial", "Vecindad de Voronoi"],
    "CPX": ["Límite polinomial", "Reducción oracular", "Obstrucción algebrizante", "Jerarquía de tiempo", "Clase BPP controlada", "Gap-ETH sentinel", "Kernelización de problema", "Heurística FPT dinámica", "Barrera natural revocada", "Complejidad termodinámica", "Completitud NP Aislada", "Teorema de Cook-Levin"],
    "DYN": ["Atractor extraño", "Exponente de Lyapunov", "Bifurcación causal", "Orbita periódica k", "Invariante de Conley", "Map-Henon discreto", "Ventana de Feigenbaum", "Sensibilidad a condiciones", "Hiper-bolicidad local", "Región de sombra", "Espacio de Fases Finito", "Fractal de Cuenca de Atracción"],
    "INF": ["Entropía de Shannon", "Ruido de canal", "Compresión de Landauer", "Capacidad de canal (C)", "Redundancia eficiente", "Código casi-perfecto", "Divergencia K-L focal", "Tasa de fuga mutua", "Síndrome de error mínimo", "Umbral de decodificación", "Teorema de Codificación de Fuente", "Entropía Cruzada"]
}

ABSTRACTIONS = ["Global", "Local", "Micro", "Macro", "Meso", "Distribuida"]
THERMODYNAMICS = ["Lógica", "Estructural", "Física", "Causal", "Informacional"]
OPERATORS = ["Producto", "Suma", "Envoltura", "Dual", "Cierre", "Extensión", "Inyección", "Retracción", "Límite", "Proyección"]

primitives = []
global_hashes = set()

def create_primitive(domain, idx, name, axiom, thermo_role, tags):
    prim_id = f"PRIM-{domain}-{idx:02d}"
    
    # Checksum to ensure no overlap
    content_str = f"{domain}:{name}:{axiom}:{thermo_role}"
    h = hashlib.sha256(content_str.encode()).hexdigest()[:8]
    
    if h in global_hashes:
        return None
    global_hashes.add(h)
    
    return {
        "id": prim_id,
        "domain": domain,
        "name": name,
        "axioma_fundador": axiom,
        "rol_termodinamico": thermo_role,
        "descripcion_sintetica": f"Operador {name.lower()} para control en el dominio de {THEORIES[domain]['name']}.",
        "tags": tags,
        "hash": h
    }

for domain, base_list in BASE_PRIMITIVES.items():
    idx = 1
    substrate = THEORIES[domain]["substrate"]
    
    # 1. Base 12 (or 10)
    for base_name in base_list:
        p = create_primitive(domain, idx, base_name, f"Axioma Núcleo {idx}", "Preservación Estructural", ["#núcleo", "#base"])
        if p:
            primitives.append(p)
            idx += 1
            
    # 2. Generate remaining up to 100
    for abs_lvl in ABSTRACTIONS:
        for therm in THERMODYNAMICS:
            for op in OPERATORS:
                if idx > 100:
                    break
                # INJECTION OF SUBSTRATE TO PREVENT CROSS-DOMAIN COLLISIONS
                name = f"{op} {abs_lvl} de Invariante {therm} sobre {substrate}"
                p = create_primitive(domain, idx, name, f"Axioma Derivado {idx}", f"Control {therm}", ["#derivada", f"#{abs_lvl.lower()}"])
                if p:
                    primitives.append(p)
                    idx += 1

out_dir = Path("babylon60/agents/primitives")
out_dir.mkdir(parents=True, exist_ok=True)
jsonl_path = out_dir / "ONTOLOGIA_BLUEPRINT_1000.jsonl"

with open(jsonl_path, "w", encoding="utf-8") as f:
    for p in primitives:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")

print(f"Generated {len(primitives)} primitives in {jsonl_path}")
