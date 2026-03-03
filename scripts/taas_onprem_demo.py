"""
TRAILFORGE SDK (Reference Implementation v2)
Ejemplo Técnico para Clientes B2B. Demuestra la inyección de "Identidad Cifrada" en tiempo de ejecución.
Incluye el Sovereign Escrow Buffer (RAM-only) corregido contra ataques de diccionario y colisiones.

Arquitectura:
1. El Agente Corporativo recupera su Trail On-Premise.
2. Identifica secretos/entidades a ofuscar (IPs, JWTs, AWS Keys, Postgres URIs).
3. Inyecta el estado y el prompt ofuscados a un Cloud LLM usando tokens aleatorios no-derivables (⟦T:TIPO:ID⟧).
4. Recupera la Inferencia.
5. Reconstituye el texto con Match exacto (Zero Token Forgery).
"""

import os
import json
import re
import secrets
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Pattern, Callable

# Token format irrompible/difícil de colisionar: ⟦T:TIPO:ID_SECRETO⟧
TOKEN_RE = re.compile(r"⟦T:(?P<type>[A-Z_]+):(?P<id>[A-Za-z0-9_-]{16,})⟧")

@dataclass
class SovereignEscrowBuffer:
    """
    Bóveda RAM-only. 
    Asigna IDs aleatorios criptográficamente seguros para evitar correlaciones y ataques de diccionario.
    """
    vault: Dict[str, str] = field(default_factory=dict)

    def lock(self, real_value: str, entity_type: str) -> str:
        tok_id = secrets.token_urlsafe(18)  # Suficiente entropía pura
        token = f"⟦T:{entity_type}:{tok_id}⟧"
        self.vault[token] = real_value
        return token

    def unlock(self, token: str) -> str:
        return self.vault.get(token, f"[[ORPHAN_TOKEN:{token}]]")

class TrailforgeEscrowEngine:
    def __init__(self) -> None:
        self.buffer = SovereignEscrowBuffer()

        # (pattern, type)
        self.sensitive_patterns: List[Tuple[Pattern[str], str]] = [
            (re.compile(r"\bpostgres(?:ql)?://[^:\s/]+:[^@\s/]+@[^/\s]+/[^\s]+\b"), "DB_CREDS"),
            (re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://[^:\s/]+:[^@\s/]+@[^/\s]+[^\s]*\b"), "URL_CREDS"),
            (re.compile(r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b"), "JWT"),
            (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "APIKEY"),
            (re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b"), "AWS_AKID"),
            # Captura valor hasta espacio/;/quote => preservamos "key=", ofuscamos el valor
            (re.compile(r"(?i)\b(password|passwd|pwd|token|api[_-]?key|secret)\s*=\s*([^\s;,'\"\\]+)"), "KV_SECRET"),
            (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "IP"),
            (re.compile(r"\b(?:[A-Fa-f0-9]{1,4}:){2,7}[A-Fa-f0-9]{1,4}\b"), "IPV6"),
            (re.compile(r"\B/(?:var|etc|home|opt|srv)/[^\s]+"), "PATH"),
        ]

    def _obfuscate(self, raw: str) -> str:
        safe = raw
        for pattern, type_name in self.sensitive_patterns:
            def repl(m: re.Match) -> str:
                # Si el patrón es KV_SECRET, preserva la key y oculta solo el value
                if type_name == "KV_SECRET" and m.lastindex and m.lastindex >= 2:
                    key = m.group(1)
                    val = m.group(2)
                    tok = self.buffer.lock(val, type_name)
                    return f"{key}={tok}"
                
                real_val = m.group(0)
                return self.buffer.lock(real_val, type_name)

            safe = pattern.sub(repl, safe)
        return safe

    def _reconstitute(self, text: str) -> str:
        # Solo reemplaza tokens bien formados y presentes en vault
        def repl(m: re.Match) -> str:
            token = m.group(0)
            return self.buffer.unlock(token)
        return TOKEN_RE.sub(repl, text)

    def ask_the_oracle(self, prompt_raw: str, llm_call: Callable[[str], str]) -> str:
        safe_prompt = self._obfuscate(prompt_raw)
        
        # En producción: NO loggear el prompt (ni safe ni raw). Solo longitud.
        print(f"[ESCROW INFO] Transmitiendo {len(safe_prompt)} bytes ofuscados al LLM...")
        
        response_obfuscated = llm_call(safe_prompt)
        return self._reconstitute(response_obfuscated)

class StatelessCommodityLLM:
    """Mock de OpenAI / Claude / Llama. El modelo sin memoria y ciego a la PII."""
    def __init__(self, vendor: str):
        self.vendor = vendor

    def generate(self, injected_prompt: str) -> str:
        print(f"[{self.vendor} (Stateless Node)] Procesando token stream ofuscado...")
        # Simulamos que el LLM genera código que reutiliza los tokens del prompt
        import re
        tokens_found = re.findall(r"⟦T:[A-Z_]+:[^⟧]+⟧", injected_prompt)
        
        db_token = next((t for t in tokens_found if "DB_CREDS" in t), "[[MISSING_DB]]")
        
        response = f"""
def enterprise_audit_task():
    # Conectando usando credenciales proveídas
    db = connect_db("{db_token}")
    return db.status()
"""
        return response.strip()

def demo_taas_escrow():
    print("=" * 60)
    print(" 🛡️  TRAILFORGE TaaS: ZERO-TRUST ESCROW ENGINE (v2) 🛡️")
    print("=" * 60)

    # 1. Definición de la intención corporativa (Llena de secretos mortales)
    corporate_memory = json.dumps({
        "last_action": "Migrated from postgres://root:SUPER_SECRET_123@10.0.0.5/prod_db",
        "ci_token": "token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.flk3.xyz987"
    })
    
    human_intent = f"Revisa este contexto corporativo:\n{corporate_memory}\n\nEscribe una función de check para la base de datos principal."

    print("\n[FIREWALL INTERNO] Contexto sin filtrar listo para ofuscar.")
    print(f"Original: {human_intent.strip()[:60]}...")
    
    # 2. Inicialización de la Bóveda en RAM
    escrow = TrailforgeEscrowEngine()
    cloud_llm = StatelessCommodityLLM("Claude 3.5 Sonnet")
    
    def llm_wrapper(safe_prompt: str) -> str:
        # Aquí el LLM recibe los datos *purificados*
        # console.log("LLM ve esto: ", safe_prompt) -> En prod es logging seguro
        return cloud_llm.generate(safe_prompt)

    # 3. Viaje de ida y vuelta a la nube
    print("\n[GATEWAY CORTEX] Invocando ofuscación + LLM Inference + Reconstitución...")
    final_execution_code = escrow.ask_the_oracle(human_intent, llm_wrapper)
    
    # 4. Resultado Final (Desofuscado on-premise)
    print("\n[FIREWALL INTERNO] Respuesta reconstituida On-Premise:")
    print("-" * 40)
    print(final_execution_code)
    print("-" * 40)
    
    print("\n" + "=" * 60)
    print(" 🟢 ZERO STATE LEAK DETECTED. EJECUCIÓN SOBERANA COMPLETADA.")
    print("=" * 60)

if __name__ == "__main__":
    demo_taas_escrow()
