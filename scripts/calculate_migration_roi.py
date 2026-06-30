# scripts/calculate_migration_roi.py
# [C5-REAL] Exergy-Maximized

import sys


def calculate_migration(monthly_tokens: int = 25000000000) -> dict:
    # 1. Consumo de Energía y Costos del Transformer (8x A100)
    # 8x A100 consume ~2.4 kW/h (300W por GPU + overhead del servidor de 400W)
    transformer_power_kw = 2.8 
    transformer_speed_tps = 50.0 # Tokens por segundo por nodo
    transformer_hourly_cost = 25.60 # 8x $3.20
    
    transformer_hours = (monthly_tokens / transformer_speed_tps) / 3600.0
    transformer_energy_kwh = transformer_hours * transformer_power_kw
    transformer_cost_usd = transformer_hours * transformer_hourly_cost
    
    # 2. Consumo de Energía y Costos de Mamba (1x A10G)
    # 1x A10G consume ~0.25 kW/h (150W por GPU + overhead del servidor de 100W)
    mamba_power_kw = 0.25
    mamba_speed_tps = 150.0
    mamba_hourly_cost = 1.00
    
    mamba_hours = (monthly_tokens / mamba_speed_tps) / 3600.0
    mamba_energy_kwh = mamba_hours * mamba_power_kw
    mamba_cost_usd = mamba_hours * mamba_hourly_cost
    
    # 3. Diferenciales y Huella de Carbono (0.385 kg CO2 por kWh)
    co2_intensity_per_kwh = 0.385
    
    saved_energy_kwh = transformer_energy_kwh - mamba_energy_kwh
    saved_co2_kg = saved_energy_kwh * co2_intensity_per_kwh
    saved_usd = transformer_cost_usd - mamba_cost_usd
    
    return {
        "monthly_tokens": monthly_tokens,
        "transformer": {
            "hours": round(transformer_hours, 2),
            "energy_kwh": round(transformer_energy_kwh, 2),
            "cost_usd": round(transformer_cost_usd, 2)
        },
        "mamba": {
            "hours": round(mamba_hours, 2),
            "energy_kwh": round(mamba_energy_kwh, 2),
            "cost_usd": round(mamba_cost_usd, 2)
        },
        "savings": {
            "energy_kwh": round(saved_energy_kwh, 2),
            "co2_metric_tons": round(saved_co2_kg / 1000.0, 2),
            "cost_usd": round(saved_usd, 2)
        }
    }

if __name__ == "__main__":
    t = 25000000000 # 25 Billones
    if len(sys.argv) > 1:
        try:
            t = int(sys.argv[1])
        except ValueError:
            pass
            
    res = calculate_migration(t)
    print(f"VOLUMEN MENSUAL: {res['monthly_tokens']} tokens")
    print("TRANSFORMER (8x A100):")
    print(f"  - Horas activas: {res['transformer']['hours']} hrs")
    print(f"  - Energía: {res['transformer']['energy_kwh']} kWh")
    print(f"  - Costo: ${res['transformer']['cost_usd']} USD")
    print("MAMBA (1x A10G):")
    print(f"  - Horas activas: {res['mamba']['hours']} hrs")
    print(f"  - Energía: {res['mamba']['energy_kwh']} kWh")
    print(f"  - Costo: ${res['mamba']['cost_usd']} USD")
    print("AHORROS DE LA MIGRACIÓN:")
    print(f"  - Energía neta salvada: {res['savings']['energy_kwh']} kWh/mes")
    print(f"  - Reducción CO2: {res['savings']['co2_metric_tons']} Toneladas Métricas/mes")
    print(f"  - Ahorro financiero neto: ${res['savings']['cost_usd']} USD/mes")
