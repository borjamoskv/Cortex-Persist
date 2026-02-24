# CORTEX v7: El Despertar de la Autopoiesis

Esta documentación detalla los cambios fundamentales introducidos en la versión 7 de CORTEX, enfocándose en la transición de un sistema de memoria pasivo a un organismo digital autorregulado.

## 🧬 Sistemas Biológicos Digitales

### 1. Autopoiesis (`experimental/autopoiesis.py`)
Inspirado en la teoría de Maturana y Varela, este módulo permite que CORTEX mantenga su propia integridad estructural.
- **Auto-sanación**: Detecta y repara "Songlines" (caminos de memoria) corruptos o huérfanos.
- **Regeneración de Historial**: Reconstruye fragmentos de ledger basados en checkpoints de Merkle si se detecta degradación silente.

### 2. Sistema Endocrino Digital (`experimental/digital_endocrine.py`)
Regula el comportamiento del enjambre mediante "hormonas" (señales químicas digitales).
- **Hormona de Estrés (Entropy-Cortisol)**: Aumenta la agresividad de las limpiezas de memoria cuando el disco o la RAM están cerca del límite.
- **Hormona de Crecimiento (Neural-Growth)**: Facilita la creación de bridges cross-project cuando la confianza en los patrones es alta (>C4).

### 3. Ciclos Circadianos (`experimental/circadian_cycle.py`)
Sincroniza el consumo de recursos con patrones de uso real u optimización térmica.
- **Fase REM**: Periodo de "sueño" donde se realiza el re-entrenamiento de vectores y la compactación de `sqlite-vec`.
- **Fase de Alerta**: Máxima respuesta para consultas en tiempo real.

---

## 🛡️ Perímetro de Seguridad Zero-Trust

La v7 eleva el estándar de seguridad mediante guardias activos en el flujo de datos:

### ConnectionGuard (`db.py`)
Interceptor de bajo nivel que valida cada conexión a la base de datos contra una firma de integridad de proceso. Previene inyecciones de red y accesos no autorizados al binario de SQLite.

### StorageGuard (`middleware/`)
Validación de hash-chain por cada escritura. Si el hash del bloque anterior no coincide, el sistema bloquea el flujo para prevenir envenenamiento de memoria.

---

## 💡 Pedagogía de Latencia: `slow_tip.py`

Para mejorar la experiencia del usuario durante operaciones pesadas (fase REM o compactación), se ha integrado un motor de tips contextuales que educa al usuario sobre la ingeniería detrás de la espera.

> [!NOTE]
> Estos sistemas se encuentran actualmente en modo experimental pero integrados en el núcleo proactivo de v7.
