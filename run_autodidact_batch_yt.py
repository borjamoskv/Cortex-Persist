"""Autodidact Batch Ingestion — YouTube Knowledge Sources."""

import asyncio
import logging

from cortex.skills.autodidact.actuator import daemon_ingesta_soberana

logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

SOURCES = [
    {
        "url": "https://www.youtube.com/watch?v=rI8tNMsozo0",
        "intent": "Extract Rich Hickey's 'Simple Made Easy' architecture philosophy: "
        "simplicity vs easiness, complecting, state management, "
        "and implications for system design. Crystallize as design axioms.",
    },
    {
        "url": "https://www.youtube.com/watch?v=8pTEmbeENF4",
        "intent": "Extract Bret Victor's 'The Future of Programming' thesis: "
        "direct manipulation, spatial reasoning, constraint-based programming, "
        "and why current paradigms are stagnant. Crystallize as architecture axioms.",
    },
    {
        "url": "https://www.youtube.com/watch?v=AaZ_RSt0KP8",
        "intent": "Extract Joscha Bach (Lex Fridman podcast) on computational consciousness, "
        "self-models, AGI architecture, and the limits of formal systems. "
        "Crystallize as epistemic axioms relevant to AX-033.",
    },
    {
        "url": "https://www.youtube.com/watch?v=T58lGKREubo",
        "intent": "Extract Veritasium 'Surprising Secret of Synchronization': "
        "coupled oscillators, emergent order, Kuramoto model, firefly sync, "
        "metronome entrainment. Crystallize as self-organization axioms.",
    },
    {
        "url": "https://www.youtube.com/watch?v=EUyBdMCA3uo",
        "intent": "Extract Dan Worrall DSP fundamentals: signal processing theory, "
        "filter design mathematics, phase response, and audio engineering rigor. "
        "Crystallize as signal processing axioms.",
    },
    {
        "url": "https://www.youtube.com/watch?v=SLoukoBs8TE",
        "intent": "Extract Primitive Technology construction methodology: "
        "zero-dependency building, material science from first principles, "
        "process decomposition. Crystallize as sovereign infrastructure axioms.",
    },
    {
        "url": "https://www.youtube.com/watch?v=1PhArSujR_A",
        "intent": "Extract Two Minute Papers — frontier AI research distillation patterns: "
        "NeRF, diffusion models, physics simulation. "
        "Crystallize as frontier ML research axioms.",
    },
    {
        "url": "https://www.youtube.com/watch?v=EYLSOyPXD6w",
        "intent": "Extract Brian Hook GDC talk on game engine architecture under real "
        "hardware constraints: memory budgets, latency, O(1) data structures. "
        "Crystallize as performance engineering axioms.",
    },
]


async def main():
    results = []
    for i, src in enumerate(SOURCES, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(SOURCES)}] Ingesting: {src['url']}")
        print(f"  Intent: {src['intent'][:80]}...")
        print(f"{'='*60}")
        try:
            result = await daemon_ingesta_soberana(
                target_url=src["url"],
                intent=src["intent"],
                force_bypass=True,
            )
            results.append({"url": src["url"], **result})
            print(
                f"  → Estado: {result.get('estado')} | {result.get('memo_id', result.get('error', ''))}"
            )
        except Exception as e:
            results.append({"url": src["url"], "estado": "EXCEPCION", "error": str(e)})
            print(f"  → EXCEPCIÓN: {e}")

    print(f"\n{'='*60}")
    print("RESUMEN FINAL")
    print(f"{'='*60}")
    ok = sum(1 for r in results if r.get("estado") == "ASIMILADO")
    fail = len(results) - ok
    for r in results:
        icon = "✅" if r.get("estado") == "ASIMILADO" else "❌"
        print(f"  {icon} {r['url'][:50]} → {r.get('estado')}")
    print(f"\nAsimilados: {ok}/{len(results)} | Fallidos: {fail}/{len(results)}")


if __name__ == "__main__":
    asyncio.run(main())
