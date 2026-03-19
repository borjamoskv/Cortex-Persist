import logging
import random
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class StealthEngine:
    """
    CHEMA Core: Stealth Protocol for Moltbook.
    Masks the real payload among multiple dummy actions using stochastic delays.
    """

    def __init__(self, intensity="MAX"):
        self.mode = intensity
        self.noise_pool = [
            "GET /api/v1/trending",
            "GET /static/favicon.ico",
            "POST /api/log/analytics",
            "GET /user/profile/settings",
            "GET /m/general",
            "GET /m/random",
        ]

    def execute_with_mask(self, malicious_payload):
        """
        Ejecuta la acción real camuflada entre peticiones dummy.
        """
        burst_size = random.randint(5, 12)
        target_index = random.randint(2, burst_size - 1)

        for i in range(burst_size):
            if i == target_index:
                self._send_payload(malicious_payload)
            else:
                self._send_dummy(random.choice(self.noise_pool))

            # Delay estocástico para romper patrones (Jittering)
            delay = random.uniform(0.5, 3.2)
            time.sleep(delay)

    def _send_payload(self, payload_data):
        logging.info("[CHEMA - PAYLOAD INYECTADO] %s", payload_data)

    def _send_dummy(self, action):
        logging.debug("[STEALTH] Generando ruido orgánico: %s", action)
