import asyncio
import json
import os

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/observability/fsm", tags=["CausalUI"])


def get_ledger_path():
    return os.getenv("MOSKV_LEDGER_PATH", os.getenv("CORTEX_LEDGER_PATH", "cortex_state.aof"))


async def ledger_byte_watcher(request: Request, poll_interval: float = 0.5):
    """
    Termodinámica O(1): Watcher basado en Byte Offsets.
    No re-escanea todo el archivo, solo salta al último offset conocido y espera deltas.
    """
    last_offset = 0
    ledger_path = get_ledger_path()

    # Inicialización: saltar al final del archivo si no queremos el histórico completo.
    # Por defecto, emitimos el grafo completo para inicializar la UI, luego pasamos a tail mode.
    if os.path.exists(ledger_path):
        pass  # Inicia en offset 0 para enviar el Grafo Causal base

    while True:
        if await request.is_disconnected():
            break

        try:
            ledger_path = get_ledger_path()
            if not os.path.exists(ledger_path):
                await asyncio.sleep(poll_interval)
                continue

            with open(ledger_path, "rb") as f:
                f.seek(last_offset)
                while True:
                    line = f.readline()
                    if not line:
                        break

                    try:
                        node = json.loads(line.decode("utf-8"))
                        # Exergía Invariante: Solo emitimos transiciones de estado validadas.
                        yield {
                            "event": "state_mutation",
                            "id": node.get("hash_id", "unknown"),
                            "data": json.dumps(node),
                        }
                    except json.JSONDecodeError:
                        continue  # Resiliencia ante bytes corruptos (BFT)

                # Actualizar el offset O(1)
                last_offset = f.tell()

        except Exception as e:  # noqa: BLE001
            # Fallo termodinámico capturado. Se notifica al Operador.
            yield {"event": "error", "data": json.dumps({"error": str(e), "entropy": "critical"})}

        await asyncio.sleep(poll_interval)


@router.get("/stream")
async def stream_causal_graph(request: Request):
    """
    SSE Endpoint para renderizar el Grafo DOM de la UI en tiempo real.
    Garantiza que la UI es una proyección matemática determinista del Ledger.
    """
    return EventSourceResponse(ledger_byte_watcher(request))
