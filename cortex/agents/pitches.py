"""
CORTEX — Pitch Arsenal.

Impossible-constraint pitches per audience.
Each designed to collapse the predictable response space and force genuine thought.

Usage::

    from cortex.agents.pitches import PITCH_CTO_SKEPTIC, PITCH_MEMO_DEV, PITCH_OS_CONTRIBUTOR
    print(PITCH_CTO_SKEPTIC)
"""

from __future__ import annotations

__all__ = [
    "PITCH_CTO_SKEPTIC",
    "PITCH_MEMO_DEV",
    "PITCH_OS_CONTRIBUTOR",
    "PITCH_COMPLIANCE_DIRECTOR",
    "PITCH_VC_FOLLOWUP",
    "PITCH_JOURNALIST",
]


# ─── 1. CTO Escéptico (90 segundos, sin EU AI Act, sin métricas) ─────

PITCH_CTO_SKEPTIC = """\
"La última vez que tu equipo deployó un agente en producción — ¿cuánto tiempo \
tardaron en responder cuando alguien preguntó qué decisión tomó y por qué?"

[Silencio.]

"Eso es el problema. No que el agente se equivocara. Sino que no había forma de saberlo."

"Tu ingeniero tiene razón: CORTEX es complejo. Pero la complejidad está en el lugar \
correcto — en la capa de verificación, no en la de negocio. Del mismo modo que TCP/IP \
es complejo y tú nunca piensas en ello, CORTEX opera por debajo del agente. \
Tu equipo no lo toca."

"La pregunta no es si necesitas esto. Ya lo necesitas — cada vez que alguien te \
pregunta si el agente tomó la decisión correcta y no tienes prueba. La pregunta es si \
prefieres construirlo tú cuando ya sea urgente, o instalarlo hoy cuando aún es Optional."

[Pausa.]

"¿Con qué frecuencia te piden auditar decisiones de agentes ahora mismo?"\
"""


# ─── 2. Developer usando Mem0 (≤280 chars, GitHub comment) ──────────

PITCH_MEMO_DEV = """\
Mem0 guarda lo que tu agente recuerda. CORTEX responde a la pregunta \
que Mem0 no puede: ¿cómo sabes que ese recuerdo es el original?

`cortex verify 42 → ✅ SHA-256 intact, Merkle sealed. 3ms.`\
"""


# ─── 3. Open Source Contributor (primera frase falseable) ───────────

PITCH_OS_CONTRIBUTOR = """\
El WBFT de CORTEX rechaza nodos con reputación-score < 0.6 usando ponderación \
bayesiana — sin coordinador central. Si crees que eso no escala a 50 nodos, \
lee cortex/consensus/wbft.py línea 147 y dime si estoy equivocado.\
"""


# ─── 4. Director de Compliance bancario (cero jerga técnica) ────────

PITCH_COMPLIANCE_DIRECTOR = """\
Imagina que cada decisión que toma tu agente de IA queda sellada en un sobre \
lacrado con la fecha y hora — y que cualquier regulador puede abrir ese sobre \
tres años después y verificar que no fue tocado.

CORTEX hace eso. Sin blockchain, sin cloud obligatorio, sin cambiar \
lo que ya tienes.

La frase que puedes repetir en el board: \
"Cada decisión de nuestros agentes tiene una huella matemática que prueba que \
no fue modificada. Podemos demostrarlo en dos minutos."\
"""


# ─── 5. VC que ya dijo "no" (4 frases, sin métricas, sin refutar) ───

PITCH_VC_FOLLOWUP = """\
La última vez hablamos de timing. Tienes razón en que el mercado no está listo.

Pero el mercado no compra CORTEX — lo compran los equipos legales de las \
empresas a las que ya inviertes, dos semanas antes de que su CTO les diga \
que no tienen audit trail para el regulador.

Ya está pasando en dos de tus portfolio companies. \
Solo quería que lo supieras antes de que llegue por otra vía.\
"""


# ─── 6. Periodista de TechCrunch / Wired (lede sin producto ni empresa) ─

PITCH_JOURNALIST = """\
En 2026, la pregunta más cara del mundo de la IA no es "¿qué sabe el agente?" \
Es: "¿puedes probar que lo sabía ayer?"

Una startup española está apostando a que esa pregunta valdrá €30 millones \
la primera vez que un regulador europeo se la haga a una empresa sin respuesta.\
"""
