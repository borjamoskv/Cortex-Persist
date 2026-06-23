import asyncio
import logging
import os
import re
import sys

sys.path.insert(0, os.path.abspath('.'))

from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.engine.autodidact_hott_engine import AutodidactHottEngine
from cortex.engine.ultramap import UltramapSubstrate

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("inject_10_ciclos")

async def inject_cycles():
    logger.info("Iniciando inyección de los 10 Ciclos AUTODIDACT en el Ledger C5-REAL...")
    
    # Instanciar el sustrato y el ledger
    ultramap = UltramapSubstrate(capacity=10000)
    ledger = EnterpriseAuditLedger(log_path=os.getenv("CORTEX_LOG_PATH", "security_audit_log.jsonl"))
    hott_engine = AutodidactHottEngine(ledger=ledger, ultramap=ultramap)
    
    md_path = "AUTODIDACT_10_CICLOS.md"
    if not os.path.exists(md_path):
        logger.error(f"Archivo {md_path} no encontrado.")
        sys.exit(1)
        
    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    # Parsear los Ciclos
    cycle_blocks = re.split(r'### CICLO ', content)[1:]
    
    agent_id = 10  # Agent ID 10 para la serie de 10 ciclos
    ultramap.update_agent_position(agent_id, 0.0, 0.0, 0.0, "AUTODIDACT_10_CICLOS_ROOT", 0.0)

    for i, block in enumerate(cycle_blocks):
        lines = block.strip().split('\n')
        header_line = lines[0].strip() # Ej: "01: Invariancia de Arquitectura Base"
        match_header = re.match(r'(\d+):\s*(.+)', header_line)
        if not match_header:
            continue
            
        cycle_num = match_header.group(1).strip()
        cycle_name = match_header.group(2).strip()
        
        # Buscar el Invariante y el Anclaje
        invariante = ""
        anclaje = ""
        for line in lines:
            if "Invariante C5-REAL:" in line:
                invariante = line.split("Invariante C5-REAL:")[1].strip()
            elif "Anclaje Técnico:" in line:
                anclaje = line.split("Anclaje Técnico:")[1].strip()
                
        axiom_claim = f"AUTODIDACT-CICLO-{cycle_num}: {cycle_name}"
        constructive_proof = f"Invariante: {invariante} | Anclaje: {anclaje}"
        
        # Filtrar caracteres de markdown molestos
        constructive_proof = constructive_proof.replace("**", "").replace("`", "")
        
        event_hash = await hott_engine.ingest_axiom(
            agent_idx=agent_id,
            axiom_claim=axiom_claim,
            constructive_proof=constructive_proof
        )
        logger.info(f"Ciclo {cycle_num} inyectado con éxito. Event Hash: {event_hash}")
        
        # Actualizar la posición en el ultramap espacial
        ultramap.update_agent_position(agent_id, float(cycle_num), 0.0, 0.0, f"AUTODIDACT_10_CICLOS_{cycle_num}", 0.2)
        
    await asyncio.sleep(0.5)
    logger.info("Inyección de los 10 Ciclos finalizada exitosamente.")

if __name__ == "__main__":
    asyncio.run(inject_cycles())
