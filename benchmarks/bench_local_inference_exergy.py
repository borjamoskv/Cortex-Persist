# [C5-REAL] Exergy-Maximized Benchmark for Local LLM Inference
# Autor: Borja Moskv
# Licencia: Apache-2.0

import math

import numpy as np

# Constantes Físicas Universales
T0 = 298.15  # Temperatura ambiente de referencia (K)
KB = 1.380649e-23  # Constante de Boltzmann (J/K)
ALPHA_LANDAUER = KB * math.log(2)  # Límite inferior de Landauer por bit (J/K)


class SiliconArchitecture:
    def __init__(
        self,
        name: str,
        memory_capacity_gb: float,
        memory_bandwidth_gbs: float,
        energy_per_bit_pj: float,
        theta_ja_kw: float,
        compute_power_base_w: float,
        model_size_gb: float,
        bits_per_weight: float,
    ):
        self.name = name
        self.memory_capacity_gb = memory_capacity_gb
        self.memory_bandwidth_gbs = memory_bandwidth_gbs
        self.energy_per_bit_j = energy_per_bit_pj * 1e-12
        self.theta_ja_kw = theta_ja_kw
        self.compute_power_base_w = compute_power_base_w
        self.model_size_gb = model_size_gb
        self.bits_per_weight = bits_per_weight


def simulate_inference(
    arch: SiliconArchitecture,
    context_length: int,
    kv_cache_bytes_per_token: float,
) -> dict:
    """
    Simula la inferencia token a token y calcula métricas termodinámicas.
    """
    latencies = []
    exergy_destroyed_steps = []
    total_energy_steps = []
    temperatures = []
    
    # Peso del modelo en bytes
    model_bytes = arch.model_size_gb * 1e9
    
    # Ancho de banda en bytes/segundo
    bw_bytes_sec = arch.memory_bandwidth_gbs * 1e9

    for k in range(1, context_length + 1):
        # Bytes de la KV-cache acumulados en el paso k
        kv_cache_bytes = k * kv_cache_bytes_per_token
        
        # Total de bytes a leer de la memoria para este token
        bytes_transferred = model_bytes + kv_cache_bytes
        bits_transferred = bytes_transferred * 8.0
        
        # Tiempo por token (saturado por ancho de banda de memoria)
        t_token = bytes_transferred / bw_bytes_sec
        latencies.append(t_token * 1000.0)  # Convertir a ms
        
        # Calor Joule disipado en la transferencia de memoria
        # Q_joule = E_bit * N_bits
        q_joule = arch.energy_per_bit_j * bits_transferred
        p_joule = q_joule / t_token if t_token > 0 else 0.0
        
        # Potencia total disipada durante el paso
        p_total = p_joule + arch.compute_power_base_w
        
        # Temperatura de la unión del silicio (Silicon Junction Temperature)
        t_chip = T0 + (arch.theta_ja_kw * p_total)
        temperatures.append(t_chip)
        
        # Ecuación de Gouy-Stodola adaptada del marco matemático formal:
        # S_gen_dot = (P_joule / T_chip) + alpha * N_bits_dot
        # X_dest_dot = T0 * S_gen_dot
        # X_dest_step = X_dest_dot * t_token = T0 * (Q_joule / T_chip + alpha * N_bits_step)
        s_gen_step = (q_joule / t_chip) + (ALPHA_LANDAUER * bits_transferred)
        x_dest_step = T0 * s_gen_step
        exergy_destroyed_steps.append(x_dest_step)
        
        # Energía total consumida en este paso (J)
        energy_step = p_total * t_token
        total_energy_steps.append(energy_step)

    # Métricas agregadas
    total_latency_ms = sum(latencies)
    total_exergy_destroyed = sum(exergy_destroyed_steps)
    total_energy_consumed = sum(total_energy_steps)
    mean_latency = np.mean(latencies)
    mean_temp = np.mean(temperatures)
    
    # Eficiencia exergética real
    exergy_efficiency = 1.0 - (total_exergy_destroyed / total_energy_consumed) if total_energy_consumed > 0 else 0.0

    return {
        "architecture": arch.name,
        "total_latency_s": total_latency_ms / 1000.0,
        "mean_latency_ms": mean_latency,
        "total_exergy_destroyed_j": total_exergy_destroyed,
        "total_energy_consumed_j": total_energy_consumed,
        "mean_temp_c": mean_temp - 273.15,
        "exergy_efficiency": exergy_efficiency,
        "latencies": latencies,
        "exergy_destroyed": exergy_destroyed_steps,
    }


def print_report():
    # Modelos y arquitecturas de silicio locales
    # Apple M3 (18 GB RAM) ejecutando Llama-3-8B Q4_K_M (4.8 GB)
    m3 = SiliconArchitecture(
        name="Apple M3 (18GB)",
        memory_capacity_gb=18.0,
        memory_bandwidth_gbs=150.0,
        energy_per_bit_pj=7.5,
        theta_ja_kw=1.8,
        compute_power_base_w=12.0,
        model_size_gb=4.8,
        bits_per_weight=4.5,
    )
    
    # Apple M5 Ultra/Max Concept (256 GB RAM) ejecutando Llama-3-70B Q8 (75 GB)
    m5_ultra = SiliconArchitecture(
        name="Apple M5 Ultra (256GB)",
        memory_capacity_gb=256.0,
        memory_bandwidth_gbs=1000.0,
        energy_per_bit_pj=3.2,
        theta_ja_kw=0.55,
        compute_power_base_w=45.0,
        model_size_gb=75.0,
        bits_per_weight=8.5,
    )
    
    # Qualcomm Snapdragon X Elite 2 (32 GB RAM) ejecutando Llama-3-8B INT4 (4.2 GB)
    snapdragon = SiliconArchitecture(
        name="Snapdragon X Elite 2",
        memory_capacity_gb=32.0,
        memory_bandwidth_gbs=135.0,
        energy_per_bit_pj=6.2,
        theta_ja_kw=1.3,
        compute_power_base_w=7.5,
        model_size_gb=4.2,
        bits_per_weight=4.0,
    )

    # Parámetros del contexto
    context_length = 4096
    
    # Asumimos KV-Cache estándar para Llama-3-8B y 70B
    # Llama 3 8B: 32 capas, 8 KV heads, head dim 128. Q8_0 KV Cache = ~2.0 MB por token en total.
    # Llama 3 70B: 80 capas, 8 KV heads, head dim 128. Q8_0 KV Cache = ~5.12 MB por token en total.
    kv_cache_bytes_8b = 32 * 2 * 8 * 128 * 2  # ~131 KB por token
    kv_cache_bytes_70b = 80 * 2 * 8 * 128 * 2  # ~327 KB por token

    print("=================================================================================")
    print("  AUDITORÍA DE SILICIO LOCAL: INFERENCIA DE LLMS BAJO TERMODINÁMICA DE LA INFORMACIÓN")
    print(f"  Contexto Simulado: {context_length} tokens | Autor: Borja Moskv | Ledged-ID: C5-REAL")
    print("=================================================================================\n")

    results = []
    for arch, kv_bytes in [
        (m3, kv_cache_bytes_8b),
        (m5_ultra, kv_cache_bytes_70b),
        (snapdragon, kv_cache_bytes_8b),
    ]:
        res = simulate_inference(arch, context_length, kv_bytes)
        results.append(res)

    # Formateo de Reporte Markdown
    print("# Matriz Termodinámica de Ejecución Local (Resultados de Simulación C4-SIM)\n")
    print("| Arquitectura Silicio | Tiempo Total (s) | Latencia Media (ms/tok) | Temp Unión Media (°C) | Energía Total (J) | Exergía Destruida (J) | Eficiencia Exergética |")
    print("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
    for r in results:
        print(
            f"| {r['architecture']} | {r['total_latency_s']:.2f}s | {r['mean_latency_ms']:.2f} ms | {r['mean_temp_c']:.1f}°C | {r['total_energy_consumed_j']:.1f} J | {r['total_exergy_destroyed_j']:.3e} J | {r['exergy_efficiency']*100:.6f}% |"
        )
    
    print("\n## 🔍 Análisis Causal de Degradación por KV-Cache")
    for r in results:
        initial_lat = r["latencies"][0]
        final_lat = r["latencies"][-1]
        lat_growth = ((final_lat - initial_lat) / initial_lat) * 100.0
        print(f"- **{r['architecture']}**:")
        print(f"  - Latencia Inicial (Token 1): {initial_lat:.2f} ms")
        print(f"  - Latencia Final (Token {context_length}): {final_lat:.2f} ms")
        print(f"  - Crecimiento de Latencia por Carga de KV-Cache: {lat_growth:.1f}%")
        print(f"  - Tasa de Destrucción de Exergía Media: {r['total_exergy_destroyed_j']/r['total_latency_s']:.3e} J/s")
    
    print("\n=================================================================================")
    print("Fin del reporte de simulación de Exergía.")
    print("=================================================================================")


if __name__ == "__main__":
    print_report()
