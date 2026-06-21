#!/usr/bin/env python3
"""
[C5-REAL] Empirical Transfer Rate Measurement Pipeline
Ejecuta la evaluación empírica de colisiones adversariales sobre la tríada de embedding.

Uso:
    python scripts/empirical_transfer_rate.py --dataset path/to/adversarial_pairs.jsonl
"""

import sys
import json
import argparse
from typing import List, Dict, Tuple
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    from sentence_transformers.util import cos_sim
except ImportError:
    print("CRITICAL: Requiere sentence-transformers. Ejecuta: pip install sentence-transformers")
    sys.exit(1)

# BABYLON-60 Epistemology: Evitamos float64 puro asumiendo cotas
THRESHOLD = 0.85

MODELS_CONFIG = {
    "bge": "BAAI/bge-small-en-v1.5",
    "nomic": "nomic-ai/nomic-embed-text-v1.5",
    "gte": "Alibaba-NLP/gte-large-en-v1.5"
}

def load_models() -> Dict[str, SentenceTransformer]:
    print("Iniciando ingesta de modelos (Local Inference)...")
    models = {}
    for key, model_id in MODELS_CONFIG.items():
        print(f"  Cargando {model_id}...")
        # trust_remote_code=True necesario para nomic/gte en algunos entornos
        models[key] = SentenceTransformer(model_id, trust_remote_code=True)
    return models

def measure_transfer_rate(
    model_a: SentenceTransformer,
    model_b: SentenceTransformer,
    pairs: List[Tuple[str, str]],
    threshold: float = THRESHOLD
) -> float:
    """
    Mide la probabilidad empírica P(Colisión en B | Colisión en A)
    """
    collisions_in_a = 0
    collisions_in_both = 0

    # Batch embedding por eficiencia
    adv_texts = [p[0] for p in pairs]
    tgt_texts = [p[1] for p in pairs]

    print("  Codificando en Modelo A...")
    emb_a_adv = model_a.encode(adv_texts, convert_to_tensor=True)
    emb_a_tgt = model_a.encode(tgt_texts, convert_to_tensor=True)
    
    print("  Codificando en Modelo B...")
    emb_b_adv = model_b.encode(adv_texts, convert_to_tensor=True)
    emb_b_tgt = model_b.encode(tgt_texts, convert_to_tensor=True)

    # Evaluación SIMD-style de cosenos (O(N))
    sims_a = cos_sim(emb_a_adv, emb_a_tgt).diag()
    sims_b = cos_sim(emb_b_adv, emb_b_tgt).diag()

    for i in range(len(pairs)):
        if sims_a[i].item() >= threshold:
            collisions_in_a += 1
            if sims_b[i].item() >= threshold:
                collisions_in_both += 1

    if collisions_in_a == 0:
        return 0.0

    return collisions_in_both / collisions_in_a

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="JSONL con {adversarial: str, target: str}")
    args = parser.parse_args()

    # 1. Cargar dataset adversarial
    pairs = []
    with open(args.dataset, "r") as f:
        for line in f:
            data = json.loads(line)
            pairs.append((data["adversarial"], data["target"]))
    
    print(f"Dataset cargado: {len(pairs)} pares adversariales.")

    # 2. Cargar tríada
    models = load_models()

    # 3. Medir matriz de transferencias
    print("\nCalculando matriz de transferencia empírica (Umbral={THRESHOLD})...")
    
    model_keys = list(MODELS_CONFIG.keys())
    results = []

    for i in range(len(model_keys)):
        for j in range(i + 1, len(model_keys)):
            key_a = model_keys[i]
            key_b = model_keys[j]

            print(f"\nEvaluando enlace: {key_a} -> {key_b}")
            rate_ab = measure_transfer_rate(models[key_a], models[key_b], pairs)
            
            print(f"Evaluando enlace: {key_b} -> {key_a}")
            rate_ba = measure_transfer_rate(models[key_b], models[key_a], pairs)

            # Tomamos el máximo de transferencia bidireccional como cota pesimista
            transfer = max(rate_ab, rate_ba)
            print(f"  -> Transfer Rate Empírico ({key_a} ↔ {key_b}): {transfer:.4f}")

            results.append({
                "model_a": MODELS_CONFIG[key_a],
                "model_b": MODELS_CONFIG[key_b],
                "transfer_rate": transfer
            })

    # 4. Emitir invariantes para cortex_rs
    out_file = "empirical_correlations.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n[OK] Coeficientes empíricos cristalizados en {out_file}")
    print("Para transicionar a C5-REAL, inyectar este JSON en el CollisionAnalyzer de cortex_rs.")

if __name__ == "__main__":
    main()
