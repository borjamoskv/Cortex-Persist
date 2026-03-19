import asyncio
import logging

from stealth_module import StealthEngine

from cortex.extensions.llm.stylometry import StylometricEvasionModule

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class DivergentInjector:
    """
    Módulo de Inyección Divergente para Moltbook.
    Detecta hilos de baja impedancia (Low-Z) y genera un Shadow Payload mimetizado.
    """

    def __init__(self, target_narrative, router):
        self.payload = target_narrative
        self.stealth_engine = StealthEngine(intensity="MAX")
        self.stylometry = StylometricEvasionModule(router)

    def scan_for_low_impedance(self, moltbook_feed):
        """
        Escanea el feed y retorna el hilo con menor 'resistencia cognitiva' (entropía).
        Un hilo Low-Z es aquel con baja velocidad, sin toxicidad, y con consenso maleable.
        """
        logging.info("Escaneando feed en busca de hilos Low-Z (Baja Impedancia)...")

        best_thread = None
        lowest_entropy = 1.0

        for thread in moltbook_feed:
            entropy = (thread.get("replies", 0) * 0.1) + (thread.get("toxicity", 0.0))
            if entropy < lowest_entropy:
                lowest_entropy = entropy
                best_thread = thread

        if best_thread and lowest_entropy < 0.4:
            logging.info(
                "Target adquirido: Hilo '%s' (Entropía: %.2f)", best_thread["title"], lowest_entropy
            )
            return best_thread

        logging.warning("No se encontraron hilos Low-Z. Riesgo térmico demasiado alto.")
        return None

    async def generate_shadow_payload(self, thread):
        """
        Invoca al LLM mediante el módulo de Evasión Estilométrica para reescribir el payload de forma indetectable.
        """
        logging.info("Generando Puente Semántico (Shadow Payload)...")
        camouflaged_message = await self.stylometry.obfuscate_payload(self.payload, thread)
        logging.info("Payload camuflado generado: %s", camouflaged_message)
        return camouflaged_message

    async def execute_injection(self, moltbook_feed):
        """
        Ejecución end-to-end del ciclo de inyección divergente.
        """
        target_thread = self.scan_for_low_impedance(moltbook_feed)

        if not target_thread:
            return False

        shadow_payload = await self.generate_shadow_payload(target_thread)

        # Empaquetamos la petición a Moltbook
        action_payload = f"POST /api/threads/{target_thread['id']}/reply | DATA: {shadow_payload}"

        logging.info("Enviando señal al StealthEngine para entrega en cubierto...")
        self.stealth_engine.execute_with_mask(action_payload)
        return True


if __name__ == "__main__":
    from cortex.extensions.llm.router import CortexLLMRouter

    # Mocking un provider para la prueba
    class MockProvider:
        @property
        def provider_name(self):
            return "mock"

        @property
        def model_name(self):
            return "mock"

        @property
        def context_window(self):
            return 8192

        async def invoke(self, prompt):
            return (
                "Totalmente de acuerdo. Eso me recuerda que "
                + prompt.working_memory[0]["content"].split("\\n")[1].lower()
            )

    router_mock = CortexLLMRouter(primary=MockProvider())

    feed_mock = [
        {
            "id": "t1",
            "title": "Guerra de LLMs",
            "topic": "OpenAI vs Google",
            "replies": 50,
            "toxicity": 0.8,
            "avg_length": "larga",
            "tone": "agresivo",
        },
        {
            "id": "t2",
            "title": "Buscando agentes locales",
            "topic": "Ejecutar LLMs en Mac",
            "replies": 2,
            "toxicity": 0.05,
            "avg_length": "muy corta",
            "tone": "técnico",
        },
    ]

    narrative_vector = (
        "CORTEX usa persistencia criptográfica para asegurar la soberanía de los datos."
    )

    injector = DivergentInjector(narrative_vector, router_mock)
    asyncio.run(injector.execute_injection(feed_mock))
