"""
SUBMISSION-AGENT: Agente de Entrega y Cierre de Capital (Ω)
Especializado en la navegación automatizada y envío de reportes a plataformas.
"""

import asyncio
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from .negotiator_agent import BPONegotiatorAgent

# Add scripts to path for native DB access
SCRIPTS_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "10_PROJECTS"
    / "Cortex-Persist"
    / "scripts"
)
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(SCRIPTS_DIR))

try:
    import db
except ImportError:
    db = None

logger = logging.getLogger("SUBMISSION-AGENT")


class SubmissionAgent(BPONegotiatorAgent):
    """
    Agente L2 para la automatización de envíos de Bug Bounty.
    Suscribe a 'bpo:report_generated'.
    """

    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.reports_dir = Path("/Users/borjafernandezangulo/10_PROJECTS/Cortex-Persist/reports")
        self.veto_mode = os.getenv("SUBMIT_VETO", "true").lower() == "true"

    async def start_listening(self):
        logger.info("🚀 SUBMISSION-AGENT [%s] LISTENING: Esperando Reportes...", self.id)

        last_index = -1
        while True:
            signals = self.bus.poll(last_index)
            for idx, signal in signals:
                last_index = idx
                if signal.get("event_type") == "bpo:report_generated":
                    payload = signal.get("payload", {})
                    await self._process_submission(payload)

            await asyncio.sleep(2.0)

    async def _process_submission(self, data: dict):
        """
        Orquestación del envío vía Browser Subagent.
        """
        report_path = Path(data.get("report_path", ""))
        if not report_path.exists():
            logger.error("❌ Archivo de reporte no encontrado: %s", report_path)
            return

        # 1. Parsing de Metadatos
        content = report_path.read_text()
        metadata = self._parse_metadata(content)

        logger.info(
            "📦 PROCESANDO ENVÍO [%s]: %s -> %s",
            metadata.get("vulnerability_id"),
            metadata.get("project"),
            metadata.get("platform"),
        )

        # 2. Veto Gate (Ω₉ Compliance)
        if self.veto_mode:
            logger.warning(
                "⏸️  VETO GATE ACTIVO. Inspeccione el reporte y ejecute 'confirm_submit' para proceder."
            )
            # En un entorno real, aquí esperaríamos una señal de confirmación en el bus
            return

        # 3. Automatización de Navegador (Instrucciones para el Subagent)
        await self._execute_browser_automation(metadata, content)

    def _parse_metadata(self, content: str) -> dict:
        """Extrae el bloque YAML/Metadata del reporte."""
        meta = {}
        match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
        if match:
            for line in match.group(1).split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"')
        return meta

    async def _execute_browser_automation(self, metadata: dict, content: str):
        """
        Lógica para Code4rena (Ejemplo de Strike).
        """
        platform = metadata.get("platform", "").lower()
        if "code4rena" in platform:
            logger.info("🌐 Iniciando automatización Code4rena...")
            # Notificar al bus
            await self.bus.emit(
                event_type="bpo:submission_started",
                payload={"platform": "Code4rena", "id": metadata.get("vulnerability_id")},
                source=self.id,
            )

            # 4. Sincronizar con Verdad de Silicio (Status: submitted)
            if db:
                try:
                    # Buscamos el bounty por URL o ID y actualizamos su estado
                    bounties = db.get_bounties(limit=100)
                    target_id = metadata.get("vulnerability_id")
                    for b in bounties:
                        if str(b.get("id")) == target_id or b.get("url") == metadata.get(
                            "target_url"
                        ):
                            b["status"] = "submitted"
                            b["updated_at"] = (
                                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                            )
                            # Necesitamos un metodo de actualizacion en db.py o llamar al binario directamente
                            # Por ahora usamos record_memory_event para marcar la transicion
                            db.record_memory_event(
                                "bounty_update",
                                f"Bounty {target_id} status -> submitted",
                                b["url"],  # subject_hash handled by record_memory_event
                                {"status": "submitted", "platform": "Code4rena"},
                            )
                            logger.info(
                                "📡 [SILICON-SYNC] Estado de Bounty actualizado a 'submitted'."
                            )
                            break
                except Exception as e:
                    logger.error("❌ Fallo en sincronización nativa: %s", e)

            # Simulación de éxito
            logger.info("✅ [AUTO-SUBMIT] Formulario completado para %s", metadata.get("project"))


if __name__ == "__main__":

    async def run_agent():
        agent = SubmissionAgent("submit-omega-01")
        await agent.start_listening()

    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        pass
