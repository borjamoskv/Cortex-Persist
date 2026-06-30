# scripts/calculate_token_pricing_sim.py
# [C5-REAL] Exergy-Maximized

import sys

def run_simulation(input_tokens: int = 900000, output_tokens: int = 100000) -> list:
    # 2026 Verified Pricing Matrix (per million tokens)
    models = {
        "Claude Opus 4.8": {"input": 5.00, "output": 25.00, "source": "Official Specs"},
        "GPT-5.5 API": {"input": 5.00, "output": 30.00, "source": "Official Specs"},
        "Gemini 3.1 Pro (Long)": {"input": 4.00, "output": 18.00, "source": "Official Specs"},
        "Grok 4.3": {"input": 1.25, "output": 2.50, "source": "Secondary Sources"}
    }
    
    results = []
    total_tokens = input_tokens + output_tokens
    
    for name, rates in models.items():
        cost_in = (input_tokens / 1000000.0) * rates["input"]
        cost_out = (output_tokens / 1000000.0) * rates["output"]
        total_cost = cost_in + cost_out
        
        results.append({
            "model": name,
            "cost_in": round(cost_in, 2),
            "cost_out": round(cost_out, 2),
            "total_cost": round(total_cost, 2),
            "source": rates["source"]
        })
        
    return results

if __name__ == "__main__":
    in_t = 900000
    out_t = 100000
    if len(sys.argv) > 2:
        try:
            in_t = int(sys.argv[1])
            out_t = int(sys.argv[2])
        except ValueError:
            pass
            
    res = run_simulation(in_t, out_t)
    print(f"SIMULACIÓN DE COSTOS (Entrada: {in_t} | Salida: {out_t})")
    for r in res:
        print(f"{r['model']} ({r['source']}): Total: ${r['total_cost']} USD (Entrada: ${r['cost_in']} | Salida: ${r['cost_out']})")
