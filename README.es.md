🌐 [English](README.md) | **Español** | [中文](README.zh.md)

# CORTEX Persist

Memoria verificable y linaje de decisiones para flujos de IA de alto riesgo.

CORTEX Persist da a los equipos que llevan IA a flujos de alto riesgo memoria verificable, linaje de decisiones a prueba de manipulación y evidencia exportable. Añade registros encadenados por hash y comandos de verificación para que los equipos puedan inspeccionar qué ocurrió en vez de reconstruirlo después.

[Inicio rápido](docs/quickstart.md) · [Instalación](docs/installation.md) · [CLI](docs/cli.md) · [API](docs/api.md) · [Seguridad](docs/SECURITY_TRUST_MODEL.md) · [Roadmap](ROADMAP.md) · [Contribuir](CONTRIBUTING.md)

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/borjamoskv/Cortex-Persist/actions/workflows/ci.yml/badge.svg)](https://github.com/borjamoskv/Cortex-Persist/actions)
[![Codecov](https://codecov.io/gh/borjamoskv/Cortex-Persist/branch/main/graph/badge.svg)](https://codecov.io/gh/borjamoskv/Cortex-Persist)
[![PyPI](https://img.shields.io/pypi/v/cortex-persist.svg)](https://pypi.org/project/cortex-persist/)

---

## Qué es

CORTEX Persist está pensado para equipos que llevan IA a flujos donde un log plano no basta.

- Guarda hechos y decisiones estructuradas.
- Encadena cada escritura en un ledger a prueba de manipulación.
- Verifica el ledger cuando necesitas evidencia, no suposiciones.
- Exporta artefactos para revisiones, auditorías e incidentes.

Convive con tu stack actual. Úsalo junto con tu base de datos, tus herramientas de observabilidad y tu búsqueda vectorial cuando tenga sentido.

## Encaja mejor en

- Flujos de agentes que pueden ejecutar acciones irreversibles.
- Procesos de soporte, aprobaciones, precios, finanzas y compliance.
- Sistemas de larga duración que necesitan transiciones de estado trazables.
- Equipos que necesitan un registro defendible después del hecho.

## No sustituye

- Plataformas de observabilidad como Datadog o ELK.
- Bases vectoriales dedicadas para recuperación efímera.
- Revisión humana, revisión legal o juicio de compliance.

## Instalación

### Desde PyPI

```bash
pip install cortex-persist
```

Después, verifica la instalación:

```bash
cortex --version
cortex init
cortex status
```

### Desde el código fuente

```bash
git clone https://github.com/borjamoskv/Cortex-Persist.git
cd Cortex-Persist
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

Para el servidor API y la superficie MCP:

```bash
pip install cortex-persist[api]
```

## Inicio rápido

```bash
# Inicializa el ledger local
cortex init

# Guarda un hecho
cortex store my-project "Redis usa skip lists para conjuntos ordenados" --tags "redis,data-structures"

# Guarda una decisión
cortex store my-project "Elegimos FastAPI en lugar de Flask por soporte async" --type decision

# Verifica la integridad
cortex verify 1
cortex ledger verify

# Genera un resumen de cumplimiento
cortex compliance-report
```

Si quieres el recorrido completo, consulta [docs/quickstart.md](docs/quickstart.md).

## Superficies experimentales opcionales

La superficie estable del producto es el núcleo de memoria verificable: hechos, búsqueda, ledger, trust y salud.

El repositorio mantiene utilidades adicionales para operación y automatización, pero no forman parte de la promesa principal del producto y pueden cambiar más rápido:

```bash
npm run model:pick -- "Texto de tarea"
npm run model:guide -- --json
npm run model:dispatch -- --json "Necesito compilar y validar el site" -- "npm run build"
npm run task:build -- --json "Compilar y validar la web"
npm run task:swarm -- --json --agents=21 "Consenso de 21 agentes para la tarea"
npm run task:perfect -- --json "Blindar y dejar el repo perfecto"
npm run task:auto -- --json "Necesito compilar, testear y cerrar validación de la web antes del deploy"
npm run test:models
```

En la capa HTTP, la app por defecto monta solo la superficie core. Para habilitar rutas experimentales de forma explícita:

```bash
export CORTEX_ENABLE_EXPERIMENTAL_API=1
uvicorn cortex.api:app --host 0.0.0.0 --port 8484
```

Consulta [docs/api.md](docs/api.md) y [scripts/README.md](scripts/README.md) para el detalle completo.

## Integración en Python

```python
import asyncio
from cortex import CortexEngine


async def main() -> None:
    engine = CortexEngine()

    fact_id = await engine.store(
        project="demo-agent",
        content="El usuario aprobó una transacción de 5.000 USD",
        fact_type="decision",
    )

    results = await engine.search("aprobación de transacción", top_k=3, project="demo-agent")
    ledger = await engine.verify_ledger()

    assert fact_id
    assert results
    assert ledger.get("valid") is True


asyncio.run(main())
```

Consulta [docs/api.md](docs/api.md) para la API HTTP y [examples/demo_canonical.py](examples/demo_canonical.py) para un demo completo de extremo a extremo.

## Estructura del repositorio

- `cortex/` - motor Python, CLI, memoria, verificación y runtime principal.
- `api/` - aplicación FastAPI y endpoints HTTP.
- `sdks/python/` y `sdks/js/` - clientes experimentales para la API hospedada.
- `src/` - páginas Astro y UI del sitio.
- `docs/` - instalación, arquitectura, seguridad y documentación operativa.
- `examples/` - demos ejecutables y ejemplos de integración.

## Documentación

- [Inicio rápido](docs/quickstart.md)
- [Instalación](docs/installation.md)
- [Referencia de CLI](docs/cli.md)
- [Referencia de API](docs/api.md)
- [Modelo de seguridad y confianza](docs/SECURITY_TRUST_MODEL.md)
- [Nomenclatura canónica](docs/NAMING.md)
- [Arquitectura](docs/architecture/overview.md)

## Licencia

Apache License 2.0. Consulta [LICENSE](LICENSE).

*Creado por [borjamoskv.com](https://borjamoskv.com) y [cortexpersist.com](https://cortexpersist.com)*
