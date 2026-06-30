# scripts/calculate_exergy_finance.py
# [C5-REAL] Exergy-Maximized

import sys


def calculate_finance(tokens: int = 1000000) -> dict:
    # 1. Parámetros del Transformer (Llama-3-70B GQA)
    layers = 80
    heads = 8
    d_head = 128
    precision_bytes = 2 # FP16
    
    # Memoria KV-Cache: 2 * 2 * layers * heads * d_head * tokens
    kv_cache_bytes = 2 * precision_bytes * layers * heads * d_head * tokens
    kv_cache_gb = kv_cache_bytes / (1024 ** 3)
    
    # Costo en AWS (8x A100 80GB necesarios para alojar 327GB de KV-Cache de forma fluida)
    # A100 Node Cost: ~$32.00 por hora. Asumiendo procesamiento a 50 t/s -> 20000 segundos.
    gpu_cost_hour = 32.00
    processing_time_hours = (tokens / 50) / 3600
    transformer_cost = processing_time_hours * gpu_cost_hour
    
    # 2. Parámetros de Mamba (SSM)
    # Memoria de estado constante: d_state * d_model * precision_bytes
    d_state = 16
    d_model = 8192
    mamba_state_bytes = d_state * d_model * precision_bytes
    mamba_state_mb = mamba_state_bytes / (1024 ** 2)
    
    # Costo en AWS (1x H100 o A10G es suficiente ya que el estado es O(1) de ~0.25 MB)
    # 1x A10G Cost: ~$1.00 por hora. Procesamiento a 150 t/s -> 6666 segundos.
    mamba_gpu_cost_hour = 1.00
    mamba_processing_time_hours = (tokens / 150) / 3600
    mamba_cost = mamba_processing_time_hours * mamba_gpu_cost_hour
    
    saving_ratio = transformer_cost / mamba_cost if mamba_cost > 0 else 0
    saving_usd = transformer_cost - mamba_cost

    return {
        "tokens": tokens,
        "transformer": {
            "kv_cache_gb": round(kv_cache_gb, 2),
            "cost_usd": round(transformer_cost, 2),
            "gpus_required": 8
        },
        "mamba": {
            "state_mb": round(mamba_state_mb, 4),
            "cost_usd": round(mamba_cost, 2),
            "gpus_required": 1
        },
        "savings": {
            "ratio": round(saving_ratio, 2),
            "usd": round(saving_usd, 2)
        }
    }

if __name__ == "__main__":
    t = 1000000
    if len(sys.argv) > 1:
        try:
            t = int(sys.argv[1])
        except ValueError:
            pass
            
    res = calculate_finance(t)
    print(f"TOKENS: {res['tokens']}")
    print(f"TRANSFORMER (KV-Cache): {res['transformer']['kv_cache_gb']} GB | Costo: ${res['transformer']['cost_usd']} USD ({res['transformer']['gpus_required']}x A100)")
    print(f"MAMBA (State Space): {res['mamba']['state_mb']} MB | Costo: ${res['mamba']['cost_usd']} USD ({res['mamba']['gpus_required']}x A10G)")
    print(f"AHORRO FINANCIERO: Ratio {res['savings']['ratio']}x | Ahorro neto: ${res['savings']['usd']} USD")
