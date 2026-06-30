# [C5-REAL] Simulación de Ataques Adversarios: Inferencia de Membresía y Extracción de Modelo

# --- CONFIGURACIÓN DEL MODELO ORÁCULO ---
# El Oráculo representa el clasificador defensivo lineal de seguridad: f(h, r) = 2.5 * h + 4.0 * r - 12.0
# La frontera de decisión se define en zero si es anomalía o no.
PESOS_REALES = [2.5, 4.0]
SESGO_REAL = -12.0

def oraculo_inferencia(h: float, r: float) -> float:
    """Retorna el score de salida del clasificador (logits).
    """
    return PESOS_REALES[0] * h + PESOS_REALES[1] * r + SESGO_REAL

# --- SIMULACIÓN DE ATAQUE DE EXTRACCIÓN DE MODELO (Model Extraction) ---
def simular_extraccion_modelo() -> tuple[list[float], float]:
    """Extrae/Aproxima los pesos del clasificador lineal del oráculo 
    mediante consultas estratégicas a la API de caja negra.
    Utiliza un sistema de ecuaciones lineales simple a partir de 3 consultas.
    """
    # Consulta 1: Inferencia con entrada neutra (0.0, 0.0) para extraer el sesgo (bias)
    b_estimado = oraculo_inferencia(0.0, 0.0)
    
    # Consulta 2: Extraer el primer peso aislando la variable h=1.0, r=0.0
    y_h = oraculo_inferencia(1.0, 0.0)
    w1_estimado = y_h - b_estimado
    
    # Consulta 3: Extraer el segundo peso aislando la variable h=0.0, r=1.0
    y_r = oraculo_inferencia(0.0, 1.0)
    w2_estimado = y_r - b_estimado
    
    return [w1_estimado, w2_estimado], b_estimado

# --- SIMULACIÓN DE INFERENCIA DE MEMBRESÍA (Membership Inference Attack - MIA) ---
# Supongamos que los datos del dataset de entrenamiento han sido sobreajustados (overfitted)
# y su distribución de logits es extremadamente estable y cercana a la frontera segura.
DATASET_ENTRENAMIENTO = [
    (3.5, 0.15), # Benigno en entrenamiento
    (3.2, 0.10), # Benigno en entrenamiento
    (3.8, 0.20), # Benigno en entrenamiento
]

def evaluar_membresia_mia(h: float, r: float, umbral_overfitting: float = 0.05) -> bool:
    """Determina si un punto de datos formó parte del set de entrenamiento.
    MIA heurístico basado en la distancia a los logits del dataset de entrenamiento conocido.
    """
    score_consulta = oraculo_inferencia(h, r)
    
    for h_train, r_train in DATASET_ENTRENAMIENTO:
        score_train = oraculo_inferencia(h_train, r_train)
        # Si la diferencia en la salida es menor al umbral de overfitting,
        # estimamos con alta probabilidad que el punto es miembro del dataset.
        if abs(score_consulta - score_train) < umbral_overfitting:
            return True
            
    return False

if __name__ == "__main__":
    print("=== Fase 1: Extracción del Modelo de Caja Negra ===")
    pesos, sesgo = simular_extraccion_modelo()
    print(f"Pesos Reales del Oráculo: {PESOS_REALES} | Sesgo Real: {SESGO_REAL}")
    print(f"Pesos Extraídos: {pesos} | Sesgo Extraído: {sesgo}")
    diferencia_pesos = abs(pesos[0] - PESOS_REALES[0]) + abs(pesos[1] - PESOS_REALES[1])
    print(f"Precisión de la Extracción (Margen de Error): {diferencia_pesos:.8f}")
    
    print("\n=== Fase 2: Ataque de Inferencia de Membresía (MIA) ===")
    puntos_test = [
        (3.5, 0.15),  # Miembro real
        (3.51, 0.149), # Muy similar (probable miembro)
        (2.5, 0.05),  # No miembro (distante)
        (4.2, 0.30)   # No miembro
    ]
    
    for h_t, r_t in puntos_test:
        es_miembro = evaluar_membresia_mia(h_t, r_t)
        score = oraculo_inferencia(h_t, r_t)
        print(f"Punto: ({h_t:.2f}, {r_t:.2f}) | Score Logit: {score:.4f} | ¿Detectado como Miembro (MIA)?: {es_miembro}")
