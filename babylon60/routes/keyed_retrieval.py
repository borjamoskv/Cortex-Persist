from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from babylon60.memory.keyed_retrieval import KeyedRetrievalIndex

router = APIRouter(prefix="/krgs", tags=["memory", "krgs"])

# Global singleton or injected dependency for the KRGS Index
krgs_index = KeyedRetrievalIndex()


class RegisterNodeRequest(BaseModel):
    keys: list[str]
    node: dict[str, Any]


class ResolveContextRequest(BaseModel):
    required_keys: list[str]


@router.post("/register")
async def register_keyed_node(request: RegisterNodeRequest):
    """
    Ingesta un nuevo nodo en el Keyed Retrieval Graph System (KRGS) y persiste el cambio.
    O(1) insertion latency.
    """
    try:
        krgs_index.register_node(request.keys, request.node)
        krgs_index.flush_to_disk()
        return {"status": "success", "hash_id": request.node.get("hash_id")}
    except ValueError as e:
        # noqa: BLE001 - Deliberate fault-isolation boundary
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/resolve")
async def resolve_keyed_context(request: ResolveContextRequest):
    """
    Extrae un subgrafo de contexto determinista pre-ordenado topológicamente
    basado en las claves solicitadas. Bypasses dense vector similarity searches.
    """
    try:
        resolved_subgraph = krgs_index.resolve_context(request.required_keys)
        return {"subgraph": resolved_subgraph}
    except Exception as e:  # noqa: BLE001
        # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flush")
async def flush_krgs_to_disk():
    """
    Fuerza la persistencia manual en MessagePack.
    """
    krgs_index.flush_to_disk()
    return {"status": "flushed"}
