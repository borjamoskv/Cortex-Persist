import asyncio
import os
import subprocess
import sys
from cortex.gateway.adapters.suno_adapter import suno_generate

async def main():
    print("◈ REWORK-Ω v1.0: Inicializando Cirugía Sónica para Vetusta Morla...")
    
    prompt = (
        "Bicep and Four Tet inspired deep rework of Vetusta Morla's 'Maldita Dulzura', "
        "melodic techno, 128 BPM, A minor dorian, euphoric dark melancholic atmosphere, "
        "recognizable emotional spanish male vocal preserved but reharmonized under minor 9th chords, "
        "club-ready 6-minute dj edit, sub-bass 40Hz heavy, granular pad texture on breakdown, "
        "16th note arpeggiator with analog warmth, snare roll 32-bar build into massive drop, "
        "instrumental focus with isolated vocal cuts."
    )
    
    # Check if credentials exist
    if not os.getenv("SUNO_API_KEY") and not os.getenv("SUNO_COOKIE"):
        print("🔴 ERROR: Válvula Espora activada. No se encontró SUNO_API_KEY ni SUNO_COOKIE.")
        print("   Por favor configure las credenciales en su entorno y vuelva a intentarlo.")
        print("   Ejemplo: export SUNO_COOKIE=\"__stripe_mid=...\"")
        
        # Guardar en CORTEX el intento abortado
        store_cortex_decision("ABORTED", "CORTEX_REJECTED - Missing credentials")
        sys.exit(1)

    print("◈ Generando track a través del gateway CORTEX -> Suno AI...")
    try:
        tracks = await suno_generate(
            prompt=prompt,
            tags="melodic techno, dark electronic, indie rework",
            title="Maldita Dulzura (Rework-Ω)",
            model="chirp-v3-5"
        )
        for t in tracks:
            print(f"✅ Rework Generado: {t.title} -> {t.audio_url} ({t.duration}s)")

        # Persist decision on success
        store_cortex_decision("COMPLETED", f"Track listos: {[t.audio_url for t in tracks]}")
        print("◈ Rework-Ω Pipeline Completado Exitosamente. C5-Static🟢")

    except Exception as e:
        print(f"🔴 ERROR en la generación: {e}")
        store_cortex_decision("FAILED", str(e))
        sys.exit(1)


def store_cortex_decision(status: str, detail: str):
    """Guarda la decisión en el ledger de CORTEX via CLI."""
    summary = f"Rework-Ω Vetusta Morla - Maldita Dulzura: {status}"
    evidence = detail
    
    # Escape quotes
    summary = summary.replace('"', '\\"')
    evidence = evidence.replace('"', '\\"')
    
    cmd = [
        "cortex", "store",
        "--type", "decision",
        "--project", "rework-sovereign-omega",
        "--summary", summary,
        "--evidence", evidence,
        "--impact", "CORTEX Rework Engine Execution",
        "--confidence", "C4"
    ]
    
    try:
        print("◈ Persistiendo entropía en el Ledger CORTEX...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print("✅ CORTEX Store Exitosa.")
        else:
            print("⚠️ CORTEX Store Falló (Posible CLI missing).")
            print("Detalles del intento:")
            print(f"Summary: {summary}\nEvidence: {evidence}")
    except Exception as e:
        print(f"⚠️ CORTEX Store No Disponible: {e}")

if __name__ == "__main__":
    asyncio.run(main())
