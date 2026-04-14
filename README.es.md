🌐 [English](README.md) | **Español** | [中文](README.zh.md)

# CORTEX Persist

**Integridad criptográfica de memoria, pistas de auditoría y linaje verificable para agentes de IA.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/borjamoskv/Cortex-Persist/actions/workflows/ci.yml/badge.svg)](https://github.com/borjamoskv/Cortex-Persist/actions)
[![Codecov](https://codecov.io/gh/borjamoskv/Cortex-Persist/branch/main/graph/badge.svg)](https://codecov.io/gh/borjamoskv/Cortex-Persist)

CORTEX es una **capa de confianza (drop-in trust layer)** para la memoria de IA. Aplica integridad criptográfica sobre cualquier almacenamiento (Mem0, Zep, o personalizado), garantizando que el estado y las decisiones de los agentes permanezcan a prueba de manipulaciones y listos para auditorías.

---

### Cómo encaja CORTEX

*   **Builders** → Añade memoria a prueba de manipulaciones a agentes existentes en 30 segundos.
*   **Compliance** → Exporta evidencia de auditoría determinista para requisitos regulatorios (EU AI Act).
*   **Infraestructura** → Envuelve tu almacén vectorial actual sin reemplazar tus embeddings ni tu lógica.

---

### Inicio Rápido

```bash
# 1. Instalar e Inicializar
pip install cortex-persist
cortex init

# 2. Almacenar una memoria (con hash SHA-256 y encadenada)
cortex memory store --agent "risk-bot" --content "Transacción marcada: Discordancia de IP"

# 3. Verificar integridad (detecta manipulación manual de la base de datos)
cortex verify ledger
```

**¿Qué acaba de pasar?**
-   **Libro de Contabilidad Inmutable**: El hecho se almacenó en un registro criptográfico de solo adición.
-   **Encadenamiento de Hash**: El registro fue encadenado mediante SHA-256 al bloque anterior.
-   **Sello Merkle**: Todo el estado fue sellado con una prueba de linaje verificable.

---

### Integración

```python
import asyncio
from cortex import CortexEngine

async def main():
    engine = CortexEngine()
    
    # Almacenar con recibo criptográfico
    receipt = await engine.store_fact(
        content="Usuario aprobó transacción de $5,000",
        fact_type="decision"
    )
    
    # Verificar prueba de integridad
    assert await engine.verify(receipt.hash) == True

asyncio.run(main())
```

---

### Rendimiento (Benchmarks)

*Instancia estándar en la nube (4 vCPU, 16GB RAM).*

| Operación | Mediana | P95 | Notas |
|:---|:---|:---|:---|
| **Memory Write** | ~18 ms | ~35 ms | Local SQLite + SHA-256 |
| **Verify Record** | ~5 ms | ~12 ms | Validación de bloque individual |
| **Merkle Seal** | ~85 ms | ~140 ms | Checkpoint de 10k registros |
| **Audit Export** | ~400 ms | ~800 ms | Traversal de linaje & PDF |

---

### Documentación

- [**Arquitectura**](docs/architecture.md) — Sellos Merkle y encadenamiento de hash.
- [**Seguridad y Confianza**](docs/SECURITY_TRUST_MODEL.md) — Invariantes criptográficas.
- [**Referencia de API**](docs/api.md) — Documentación completa de SDK y CLI.

---

### Licencia

Apache License 2.0. Consulta [LICENSE](LICENSE).

*Creado por [borjamoskv.com](https://borjamoskv.com) · [cortexpersist.com](https://cortexpersist.com)*
