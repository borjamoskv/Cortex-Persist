🌐 [English](README.md) | **Español** | [中文](README.zh.md)

# CORTEX Persist

**Integridad criptográfica de memoria, pistas de auditoría y linaje verificable para agentes de IA.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/borjamoskv/Cortex-Persist/actions/workflows/ci.yml/badge.svg)](https://github.com/borjamoskv/Cortex-Persist/actions)
[![Codecov](https://codecov.io/gh/borjamoskv/Cortex-Persist/branch/main/graph/badge.svg)](https://codecov.io/gh/borjamoskv/Cortex-Persist)
[Inicio Rápido](#inicio-rápido) · [Demo Canónica](docs/canonical-demo.md) · [Core Soportado](docs/supported-core.md) · [Arquitectura](docs/architecture.md) · [Seguridad y Confianza](docs/SECURITY_TRUST_MODEL.md)

CORTEX es una **capa de confianza (drop-in trust layer)** para la memoria de IA. Aplica integridad criptográfica sobre cualquier almacenamiento (Mem0, Zep, o personalizado), haciendo el estado y las decisiones de los agentes verificables y detectables ante manipulación.

---

### Core Soportado Hoy

La superficie pública soportada hoy es más estrecha que el repositorio completo:

- **Instalación soportada**: clonado del repositorio + `pip install .`
- **Import público de Python**: `cortex_persist`
- **Flujo CLI soportado**: `init`, `store`, `recall`, `search`, `verify`, `trust-ledger verify --full`, `export`, `status`
- **Modo API**: self-hosted desde source con `pip install -e ".[api]"`, actualmente beta
- **Fuera del core soportado**: publicación pública en PyPI/npm, superficies amplias de swarm/orquestación y managed cloud

Si estás evaluando el producto por primera vez, empieza por la [Demo Canónica](docs/canonical-demo.md) y usa [Core Soportado](docs/supported-core.md) como frontera del contrato.

---

### Cómo encaja CORTEX

*   **Builders** → Añade una capa de evidencia sobre agentes existentes con una integración corta.
*   **Compliance** → Genera evidencia técnica útil para revisiones regulatorias y auditorías.
*   **Infraestructura** → Envuelve tu almacén vectorial actual sin reemplazar tus embeddings ni tu lógica.

Frente a logs o una base vectorial sola, CORTEX no vende observabilidad ni retrieval: vende evidencia verificable sobre qué sabía un agente, qué decidió y si ese registro fue alterado después.

---

### Readiness Empresarial

Si estás evaluando CORTEX para compra, procurement o adopción interna, empieza por:

- [Enterprise Readiness](ENTERPRISE_READINESS.md)
- [Due Diligence Checklist](DUE_DILIGENCE_CHECKLIST.md)
- [Deployment Hardening](DEPLOYMENT_HARDENING.md)
- [Support](SUPPORT.md)
- [Repo Governance](REPO_GOVERNANCE.md)
- [Maintainers](MAINTAINERS.md)
- [Version Support](VERSION_SUPPORT.md)
- [Release Process](RELEASE_PROCESS.md)

---

### Inicio Rápido

La vía soportada hoy es instalar desde este repositorio mientras se cierra la publicación pública en PyPI.
El paquete mantiene `cortex` como ruta operativa para CLI y API, mientras que el import público de Python es `cortex_persist`.

```bash
# 1. Clonar, instalar desde el repositorio e inicializar
git clone https://github.com/borjamoskv/Cortex-Persist.git
cd Cortex-Persist
pip install .
cortex init

# 2. Almacenar una memoria (con hash SHA-256 y encadenada)
cortex store risk-bot "Transacción marcada: Discordancia de IP" --type decision --source agent:risk-bot

# 3. Verificar el ledger y el conjunto de hechos
cortex trust-ledger verify --full
```

La [Demo Canónica](docs/canonical-demo.md) añade la verificación por fact, la simulación de tamper y la exportación de evidencia.

**¿Qué acaba de pasar?**
-   **Libro de Contabilidad Inmutable**: El hecho se almacenó en un registro criptográfico de solo adición.
-   **Encadenamiento de Hash**: El registro fue encadenado mediante SHA-256 al bloque anterior.
-   **Checkpoints Merkle**: Puedes generar y verificar pruebas por lote cuando necesites snapshots auditables del estado.

---

### Integración

```python
import asyncio
from cortex_persist import CortexEngine

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
| **Audit Export** | ~400 ms | ~800 ms | Traversal de linaje y exportación de evidencia |

---

### Documentación

- [**Demo Canónica**](docs/canonical-demo.md) — Prueba reproducible de store → verify → tamper detection → export.
- [**Core Soportado**](docs/supported-core.md) — Contrato exacto que hoy se puede prometer.
- [**Arquitectura**](docs/architecture.md) — Sellos Merkle y encadenamiento de hash.
- [**Seguridad y Confianza**](docs/SECURITY_TRUST_MODEL.md) — Invariantes criptográficas.
- [**Tecnologías Nativas de CORTEX**](docs/cortex-native-technologies.md) — Definición canónica de las cinco tecnologías exclusivas del sistema.
- [**Referencia de API**](docs/api.md) — Documentación completa de SDK y CLI.
- [**Enterprise Readiness**](ENTERPRISE_READINESS.md) — Estado actual, límites y plan de evaluación.
- [**Due Diligence Checklist**](DUE_DILIGENCE_CHECKLIST.md) — Checklist reproducible para compradores y equipos técnicos.
- [**Support**](SUPPORT.md) — Política de soporte y canales.
- [**Repo Governance**](REPO_GOVERNANCE.md) — Propiedad, revisión y seguridad de cambios.
- [**Maintainers**](MAINTAINERS.md) — Modelo de stewardship actual.
- [**Version Support**](VERSION_SUPPORT.md) — Expectativas por línea de release.
- [**Release Process**](RELEASE_PROCESS.md) — Flujo de release Python y signing.
- [**Operations**](docs/OPERATIONS.md) — Runbooks y postura operativa.
- [**Roadmap**](ROADMAP.md) — Fases de despliegue y escala.
- [**Contributing**](CONTRIBUTING.md) — Flujo de contribución.

---

### Cinco Tecnologías Nativas de CORTEX

CORTEX no solo tiene módulos; también compone cinco tecnologías propias sobre su frontera de confianza:

1. **Criptoepistemología Persistente**: decide si una salida generada merece convertirse en estado durable.
2. **Forénsica de Continuidad Hash**: demuestra que la cadena de custodia no fue alterada.
3. **Memoria Conjetural Encapsulada**: mantiene hipótesis, contradicciones y taint sin disfrazarlas de verdad.
4. **Sagas de Integridad Autónoma**: hace que cada mutación no trivial sea abortable, compensable y reversible.
5. **Autopoiesis Verificada de Agentes**: permite que los agentes sinteticen lógica nueva bajo aislamiento y validación.

La definición técnica y el mapeo a módulos reales viven en [Tecnologías Nativas de CORTEX](docs/cortex-native-technologies.md).

---

### Licencia

Apache License 2.0. Consulta [LICENSE](LICENSE).

*Creado por [borjamoskv.com](https://borjamoskv.com) · [cortexpersist.com](https://cortexpersist.com)*
