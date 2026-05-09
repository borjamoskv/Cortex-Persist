# Curso · Memoria Persistente en Agentes IA

## Objetivo

Entender la memoria persistente como subsistema arquitectónico y no como cache, transcript store o truco de búsqueda vectorial.

## Anclas del repo

- [Quickstart](../../quickstart.md)
- Internals de memoria: `architecture/CORTEX_MEMORY_INTERNALS.md`
- [Tutorial LangChain](../../tutorials/langchain.md)
- Servidor MCP: `cortex/mcp/server.py`
- Ejemplo básico de memoria: `examples/quickstart/basic_memory.py`

## Qué aprendes

- Diferencia entre almacenamiento, recuperación y memoria verificable.
- Por qué la calidad de memoria depende de semántica de confianza y no solo de recall.
- Cómo integrar memoria persistente en frameworks de agentes.
- Dónde deriva el sistema cuando se mezclan transporte, retrieval y trust.

## Labs

- Compara historial conversacional frente a memoria persistente.
- Define tres hechos que deben sobrevivir a un reset de sesión.
- Diseña un bootstrap de memoria para cold start usando este repo.

## Criterio de salida

Puedes describir la memoria persistente como sistema gobernado con write-path, read-path, trust-path y export-path.
