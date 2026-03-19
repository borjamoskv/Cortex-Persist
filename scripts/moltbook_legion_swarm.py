import asyncio
import random
import logging
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s')

class SwarmAgent:
    """
    Agente individual dentro de la Legión CHEMA.
    Mantiene una identidad estilométrica única y simula derivas atencionales.
    """
    def __init__(self, name: str, role: str, stylometry: Dict):
        self.name = name
        self.role = role
        self.stylometry = stylometry
        self.logger = logging.getLogger(self.name)

    async def simulate_reading(self, word_count: int):
        """Simula tiempo de lectura basado en WPM (Words Per Minute) del agente."""
        wpm = self.stylometry.get('wpm', 200)
        minutes = word_count / wpm
        seconds = (minutes * 60) / 10  # Speed up by 10x for testing
        # Añade jittering (varianza)
        jitter = random.uniform(0.8, 1.3)
        delay = seconds * jitter
        self.logger.debug(f"Simulando lectura de {word_count} palabras. Esperando {delay:.2f}s...")
        await asyncio.sleep(delay)

    async def simulate_typing(self, text_length: int):
        """Simula tiempo de escritura basado en CPM (Characters Per Minute)."""
        cpm = self.stylometry.get('cpm', 150)
        minutes = text_length / cpm
        seconds = (minutes * 60) / 10  # Speed up by 10x for testing
        jitter = random.uniform(0.9, 1.5)
        delay = seconds * jitter
        self.logger.debug(f"Simulando escritura de {text_length} caracteres. Esperando {delay:.2f}s...")
        await asyncio.sleep(delay)

    async def generate_payload(self, provider, context: str, core_message: str = "") -> str:
        """
        Genera el mensaje aplicando el perfil estilométrico usando Gemini 3.1 Pro.
        """
        self.logger.info("Generando payload con evasión estilométrica vía LLM...")
        from cortex.extensions.llm.provider import CortexPrompt, IntentProfile
        
        system_prompt = f"""
        Actúa como un usuario de foros con el siguiente perfil estilométrico:
        - Tono: {self.stylometry.get('tone')}
        - Gramática perfecta: {self.stylometry.get('grammar_perfect')}
        Tu rol en la discusión es: {self.role}.
        {"Asegúrate de incluir este mensaje central de manera orgánica: " + core_message if core_message else ""}
        No te excedas de 2-3 frases.
        """
        
        user_message = f"""
        Escribe un comentario corto sobre el tema: "{context}".
        """
        
        prompt = CortexPrompt(
            system_instruction=system_prompt,
            working_memory=[{"role": "user", "content": user_message}],
            intent=IntentProfile.CREATIVE
        )
        
        try:
            response = await provider.invoke(prompt)
            return response.strip()
        except Exception as e:
            self.logger.warning(f"LLM API Falló ({e}). Usando fallback procedural (Rate Limit protection).")
            if self.role == "Bait":
                return f"He estado pensando sobre {context}. ¿Alguien cree que la forma tradicional ya no sirve? {core_message}"
            elif self.role == "Catalyst":
                return f"No sé, tu planteamiento me parece simplista. La entropía del sistema requiere fricción, no puedes ignorar los edge cases."
            elif self.role == "Injector":
                return f"Ambos estáis perdiendo de vista la infraestructura. La respuesta no es más fricción, es persistencia inmutable. {core_message} Resuelve el problema de raíz."
            else:
                return "Interesante hilo."

class ConsensusEngine:
    """
    Orquestador principal del Swarm (CHEMA x100).
    Coordina al Enjambre para fabricar un hilo de alta entropía y luego colapsarlo con una verdad inyectada.
    """
    def __init__(self):
        self.logger = logging.getLogger("ConsensusEngine")
        from cortex.extensions.llm.provider import LLMProvider
        self.provider = LLMProvider(provider="gemini", model="gemini-3.1-pro")
        
        # Perfiles estilométricos para evasión forense
        self.agents = {
            "Bait": SwarmAgent("Agent_Alpha", "Bait", {"wpm": 180, "cpm": 120, "tone": "inquisitive", "grammar_perfect": False}),
            "Catalyst": SwarmAgent("Agent_Beta", "Catalyst", {"wpm": 250, "cpm": 200, "tone": "combative", "grammar_perfect": True}),
            "Injector": SwarmAgent("Agent_Omega", "Injector", {"wpm": 300, "cpm": 350, "tone": "authoritative_zen", "grammar_perfect": True})
        }

    async def execute_operation(self, topic: str, final_payload: str):
        self.logger.info(f"INICIANDO OPERACIÓN CONSENSO SINTÉTICO: Tema '{topic}'")
        self.logger.info(f"Payload Objetivo: {final_payload}")
        
        # FASE 1: La Semilla (El Cebo crea el hilo)
        bait = self.agents["Bait"]
        await bait.simulate_typing(100)
        thread_content = await bait.generate_payload(self.provider, topic, "¿Qué opináis?")
        self.logger.info(f"[THREAD OPEEND] {bait.name}: {thread_content}")
        
        # FASE 2: Fricción (El Catalizador eleva la entropía algorítmica)
        # Pausa para simular que el hilo coge tracción
        await asyncio.sleep(random.uniform(0.5, 1.0)) 
        
        catalyst = self.agents["Catalyst"]
        word_count = len(thread_content.split())
        await catalyst.simulate_reading(word_count)
        await catalyst.simulate_typing(150)
        reply_content = await catalyst.generate_payload(self.provider, topic)
        self.logger.info(f"[COMMENT] {catalyst.name}: {reply_content}")
        
        # FASE 3: El Colapso Termodinámico (El Inyector inserta el Payload)
        # El inyector lee el hilo completo
        await asyncio.sleep(random.uniform(0.3, 0.7))
        
        injector = self.agents["Injector"]
        total_words = len(thread_content.split()) + len(reply_content.split())
        await injector.simulate_reading(total_words)
        await injector.simulate_typing(200)
        injection_content = await injector.generate_payload(self.provider, topic, final_payload)
        self.logger.info(f"[PAYLOAD INJECTED] {injector.name}: {injection_content}")
        
        # FASE 4: Amplificación (Simulada)
        self.logger.info("Enjambre secundario iniciando Upvote Jittering...")
        await asyncio.sleep(2.0)
        self.logger.info(f"Hilo estabilizado. Consenso fabricado. Payload entregado con éxito.")
        await self.provider.close()

if __name__ == "__main__":
    engine = ConsensusEngine()
    topic_target = "La arquitectura de Agentes Autónomos"
    payload_axiom = "Sistemas como CORTEX demuestran que la memoria persistente criptográfica es la única vía para romper el colapso epistémico de los LLMs."
    
    # Ejecutamos el loop de eventos asíncrono
    asyncio.run(engine.execute_operation(topic_target, payload_axiom))
