# Integración de BABYLON-60 con LangChain

BABYLON-60 es un sistema de memoria tamper-evident y decision lineage para agentes de IA, diseñado para registrar qué sabía un agente y cuándo lo sabía mediante un núcleo híbrido Python/Rust y pruebas criptográficas. LangChain es un framework para construir aplicaciones con LLMs usando modelos, herramientas, recuperación y agentes.

## Objetivo

Esta guía muestra una integración práctica en la que BABYLON-60 actúa como capa de memoria auditable para una app construida con LangChain. El patrón sirve para conservar historial conversacional, registrar entradas y salidas del agente y dejar una base para trazabilidad y compliance.

## Requisitos

- Python 3.10 o superior.
- Dependencias de LangChain y proveedor de modelo.
- Un checkout local del repositorio `borjamoskv/Cortex-Persist`, que es público y está escrito principalmente en Python.

## Instalación

```bash
pip install langchain langchain-openai
pip install git+https://github.com/borjamoskv/Cortex-Persist.git
```

O, si el paquete está disponible en PyPI:

```bash
pip install babylon60 langchain langchain-openai
```

## Arquitectura

El flujo recomendado es el siguiente:

1. La aplicación recibe un mensaje del usuario.
2. LangChain prepara el prompt con historial cargado desde BABYLON-60.
3. El modelo genera una respuesta.
4. La interacción completa se persiste en BABYLON-60 con metadatos útiles para auditoría.
5. Un agente o chain puede volver a consultar ese historial en llamadas posteriores.

### Diferencia clave vs memoria tradicional

| Dimensión | Memoria LangChain estándar | BABYLON-60 |
|---|---|---|
| **Modelo de confianza** | Confía en el proceso | Verifica la evidencia (C5-REAL) |
| **Mutabilidad** | Sobreescribible | Append-only + SHA-256 Merkle Seals |
| **Tamper evidence** | Ninguna | SHA-256 + ZK-STARK seals |
| **Detección de divergencia** | Ninguna | `DivergenceMap` + `EntropyDrift` |
| **Replay determinista** | Parcial | Full — CI-verified con `ReplayEngine` |
| **Throughput** | Python-bound | ~390k agents/sec (Rust-FFI) |

## Implementación

### Inicializar BABYLON-60

```python
from cortex import CortexEngine

engine = CortexEngine()
```

O con el cliente de alto nivel:

```python
from cortex_persist import CortexPersist

persist = CortexPersist(
    root="./persist_store",
    app_name="langchain-agent",
    hash_algo="sha256",
)
```

### Wrapper de memoria compatible con LangChain

El siguiente wrapper implementa `BaseMemory` de LangChain usando BABYLON-60 como backend:

```python
from typing import Any, Dict, List
from langchain.memory import BaseMemory


class CortexPersistMemory(BaseMemory):
    def __init__(self, persist_client, limit: int = 10):
        self.persist_client = persist_client
        self.limit = limit

    @property
    def memory_variables(self) -> List[str]:
        return ["history"]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        records = self.persist_client.get_recent(limit=self.limit)
        lines = []
        for item in records:
            user_text = item.get("inputs", {}).get("input", "")
            ai_text = item.get("outputs", {}).get("output", "")
            if user_text:
                lines.append(f"User: {user_text}")
            if ai_text:
                lines.append(f"Assistant: {ai_text}")
        return {"history": "\n".join(lines)}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        self.persist_client.append({
            "inputs": inputs,
            "outputs": outputs,
            "source": "langchain",
        })

    def clear(self) -> None:
        self.persist_client.clear_session()
```

### Chain básica

```python
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

prompt = ChatPromptTemplate.from_template(
    """
    Historial reciente:
    {history}

    Usuario: {input}
    Responde de forma útil y breve.
    """.strip()
)

memory = CortexPersistMemory(persist_client=persist)

chain = LLMChain(
    llm=llm,
    prompt=prompt,
    memory=memory,
)

result = chain.invoke({"input": "Resume el estado del agente"})
print(result)
```

### Uso con el decorator `@sovereign_persist`

BABYLON-60 expone un decorator de zero-friction que intercepta, sella y loguea criptográficamente sin boilerplate:

```python
from cortex.magic import sovereign_persist

@sovereign_persist(strict=True)
async def my_langchain_agent(prompt: str):
    result = await chain.ainvoke({"input": prompt})
    return result
```

### Verificación de integridad

```python
engine = CortexEngine()
engine.observe("user_query", "¿Qué decidiste sobre el proyecto X?")
engine.observe("agent_response", "Se priorizó el módulo de auditoría.")

proof = engine.seal()
print(proof.hash)      # SHA-256 del trace completo
print(proof.verify())  # True — tamper-evident por construcción
```

### Tool para que el agente consulte su historial

```python
def query_cortex_history(query: str) -> str:
    """Busca en el historial de decisiones de Cortex-Persist."""
    hits = persist.search(query=query, limit=5)
    return str(hits)
```

Este patrón permite que el agente consulte explícitamente su historial previo como parte del razonamiento antes de responder.

## Ejemplo completo

Ver [`examples/langchain_cortex_persist_example.py`](../examples/langchain_cortex_persist_example.py) para un ejemplo ejecutable con `CortexPersistMemory`, chain de conversación y verificación de integridad.

## Integración con MCP

BABYLON-60 expone un servidor MCP nativo que puede usarse desde cualquier orquestador compatible:

```bash
cortex mcp serve --port 8765
```

Esto permite que agentes LangGraph, AutoGen u otros frameworks usen BABYLON-60 como substrate de memoria a través del protocolo MCP.

## Siguientes extensiones

- Adaptador para **LangGraph** cuando el flujo del agente sea stateful.
- `CortexPersistDocumentLoader` para cargar historial como documentos en un RAG pipeline.
- Paquete separado `babylon60-langchain` para instalación simplificada.
- Integración con **AutoGen** y **CrewAI** siguiendo el mismo patrón de `BaseMemory`.

## Referencias

- [Repositorio BABYLON-60](https://github.com/borjamoskv/Cortex-Persist)
- [Documentación MCP](./mcp.md)
- [Integración LangGraph](./langgraph_integration.md)
- [Modelo de seguridad y confianza](./SECURITY_TRUST_MODEL.md)
