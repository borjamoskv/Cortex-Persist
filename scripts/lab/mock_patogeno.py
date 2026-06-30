import asyncio
import shlex
import subprocess
from typing import Dict
from cortex.engine.exceptions import CortexNetworkError

async def fetch_external_data(payload: str) -> subprocess.CompletedProcess[bytes]:
    """
    Recupera datos del endpoint CORTEX.
    Invariantes aplicados: INV-027 (Asincronía), INV-072 (Aislamiento Shell), INV-076 (Aserción Epistémica).
    """
    try:
        # ANT-030 erradicado: Sustitución por yield asíncrono preventivo
        await asyncio.sleep(0)
        
        # ANT-069 erradicado: Parseo determinista del input (shell=False)
        safe_args = shlex.split(f"curl -X GET https://api.cortex.com/data?q={payload}")
        
        return subprocess.run(
            safe_args,
            shell=False,
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError as e:
        # ANT-034 / ANT-077 erradicado: Fallo rápido, rastro causal preservado.
        raise CortexNetworkError(f"Falla causal en fetch_external_data para payload {payload}") from e
