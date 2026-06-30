import json
import hashlib
from pathlib import Path

# Data from the user's blueprint
THEORIES = {
    "CAT": "Teoría de Categorías",
    "THD": "Termodinámica de la Computación",
    "CAU": "Inferencia Causal Estructural",
    "TYP": "Teoría de Tipos Homotópicos",
    "BFT": "Tolerancia Bizantina / Diseño de Mecanismos",
    "CYB": "Cibernética de Segundo Orden",
    "TOP": "Topología Algebraica / Grafos Complejos",
    "CPX": "Complejidad Computacional",
    "DYN": "Sistemas Dinámicos / Caos",
    "INF": "Física de la Información"
}

BASE_PRIMITIVES = {
    "CAT": [
        "Functor de preservación de estado",
        "Transformación natural (mutación topológica)",
        "Límite / colímite (consenso de enjambre)",
        "Endofunctor de compactación de contexto",
        "Fibrado Grothendieck de dependencias",
        "Adjunción costo-beneficio (dualidad energ.)",
        "Co-equalizador de versiones (merge seguro)",
        "Producto tensorial de trazas",
        "Yoneda lift (observador embebido)",
        "Colax-functor de degradación semántica"
    ],
    "THD": [
        "Límite de Landauer (borrado mínimo)",
        "Exergía computacional disponible",
        "Disipación estocástica (anergía)",
        "Gradiente entálpico de código",
        "Pozo de entropía latente",
        "Ciclo de Carnot digital",
        "Umbral de reversibilidad lógica",
        "Bomba de negentropía (compresión)",
        "Difusión térmica de memoria",
        "Frontera exobita (bit > 10⁻²¹ J)"
    ],
    "CAU": [
        "Operador do(x) (intervención)",
        "Colisionador causal",
        "D-separación de tenantes",
        "Back-door shield (control de confusores)",
        "Front-door relay (variable mediadora)",
        "Contrafáctico mínim-acción",
        "Grafo de intención (policy DAG)",
        "Causal fingerprint (huella de origen)",
        "Paradoja de Simpson vigilada",
        "Umbral de identifiabilidad"
    ],
    "TYP": [
        "Tipo dependiente",
        "Identidad proposicional",
        "Habitabilidad de tipo",
        "Path-type de equivalencia",
        "Higher-inductive constructor",
        "Truncación n-tipo (cota de abstr.)",
        "Eliminador de unicornio (proof irrelevance)",
        "Gluing lemma (pegado de módulos)",
        "Modalidad de necesidad ⬜",
        "Universo jerárquico (Uᵢ)"
    ],
    "BFT": [
        "Quorum mayoritario",
        "Sybil forzado",
        "Equilibrio de Nash asimétrico",
        "Commit-reveal aleatorizado",
        "Slashing de confianza",
        "Votación ponderada por stake-exergía",
        "Gossip anti-eclipse",
        "Umbral f < n/3 dinámica",
        "Timeout adaptativo",
        "Fair-ordering mempool"
    ],
    "CYB": [
        "Bucle de retroalimentación negativa",
        "Observabilidad del estado",
        "Histéresis cognitiva",
        "Ganancia homeostática variable",
        "Meta-control (observador del observador)",
        "Buffer antiflaping",
        "Latencia de percepción controlada",
        "Ajuste punto-de-referencia (set-point)",
        "Inercia de mando distribuido",
        "Reflexividad recursiva"
    ],
    "TOP": [
        "Número de Betti",
        "Isomorfismo de subgrafos",
        "Centralidad de autovector",
        "Homología persistente",
        "Filtro de comunidad Louvain",
        "Walk-entropy descriptor",
        "Puente de Cheeger (cuello de botella)",
        "Contractibilidad parcial",
        "Curvatura de Ollivier-Ricci",
        "Retráctil de núcleo (core)"
    ],
    "CPX": [
        "Límite polinomial",
        "Reducción oracular",
        "Obstrucción algebrizante",
        "Jerarquía de tiempo (DTIME)",
        "Clase BPP controlada",
        "Gap-ETH sentinel",
        "Kernelización de problema",
        "Heurística FPT dinámica",
        "Barrera natural revocada",
        "Complejidad termodinámica (E · t)"
    ],
    "DYN": [
        "Atractor extraño",
        "Exponente de Lyapunov",
        "Bifurcación causal",
        "Orbita periódica k",
        "Invariante de Conley",
        "Map-Henon discreto",
        "Ventana de Feigenbaum",
        "Sensibilidad a condiciones iniciales",
        "Hiper-bolicidad local",
        "Región de sombra (shadowing)"
    ],
    "INF": [
        "Entropía de Shannon",
        "Ruido de canal",
        "Compresión de Landauer",
        "Capacidad de canal (C)",
        "Redundancia eficiente (r ≤ H)",
        "Código casi-perfecto (LDPC-∞)",
        "Divergencia K-L focal",
        "Tasa de fuga mutua",
        "Síndrome de error mínimo",
        "Umbral de decodificación"
    ]
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
        "descripcion_sintetica": f"Operador {name.lower()} para control termodinámico en {domain}.",
        "tags": tags,
        "hash": h
    }

# Generate 100 per theory
for domain, base_list in BASE_PRIMITIVES.items():
    idx = 1
    # 1. Base 10
    for base_name in base_list:
        p = create_primitive(domain, idx, base_name, f"Axioma Núcleo {idx}", "Preservación Estructural", ["#núcleo", "#base"])
        if p:
            primitives.append(p)
            idx += 1
            
    # 2. Generate 90 more
    for abs_lvl in ABSTRACTIONS:
        for therm in THERMODYNAMICS:
            for op in OPERATORS:
                if idx > 100:
                    break
                name = f"{op} {abs_lvl} de Invariante {therm}"
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
