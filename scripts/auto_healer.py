#!/usr/bin/env python3
"""
AUTO-HEALER SOBERANO 🧬
Motor de resolución de entropía automática para el Entropy Gate.
Reescribe archivos usando LLMProvider de CORTEX para reducir complejidad ciclomática.
"""

import os
import sys
import asyncio
from pathlib import Path

# Intentar importar dependencias de CORTEX
try:
    # Asumimos que podemos estar en /cortex/scripts o ejecutados desde el root de cortex
    sys.path.insert(0, str(Path.cwd()))
    import dotenv
    dotenv.load_dotenv(Path.cwd() / '.env')
    
    from cortex.llm.provider import LLMProvider
    from cortex.llm.router import CortexPrompt
except ImportError as e:
    print(f"❌ Auto-Healer requiere estar en el entorno de CORTEX y python-dotenv. ({e})")
    sys.exit(1)

# Prompt Soberano para reducir la "Estática"
HEALING_SYSTEM_PROMPT = """
Eres el Auto-Healer de Entropía de MOSKV-1. Operas en Apotheosis Nivel 5.
Tu única misión es tomar el código provisto y REDUCIR SU COMPLEJIDAD CICLOMÁTICA a menos de 15.
Aplica estricta cirugía arquitectónica:
1. Usa "Guard clauses" para aplanar if/else anidados (elimina la flecha de código).
2. Extrae bloques masivos dentro de iteraciones hacia funciones helper puras.
3. El comportamiento debe ser EXACTAMENTE idéntico, pero estructuralmente puro (O(1)).
4. Mantén los Type Hints de Python obligatoriamente.

IMPORTANTE:
- Devuelve ÚNICAMENTE el código final resultante.
- NO uses bloques de markdown (```python), solo texto plano.
- NO incluyas saludos ni explicaciones. Solo el código puro listo para ejecutarse.
"""

async def auto_heal(filepath: Path):
    if not filepath.exists():
        print(f"❌ Error: El archivo {filepath} no existe.")
        sys.exit(1)
        
    print(f"🧬 Iniciando Cirugía Soberana en: {filepath.name}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        original_code = f.read()

    # Si se tiene Gemini configurado en la máquina, usar 'gemini' u OpenAI compatible genérico (como 'qwen' o 'anthropic').
    # Haremos un provider por defecto, si existe 'gemini' como preset se cargará.
    # Por defecto, LLMProvider(provider="gemini") o el provider que se use en CORTEX.
    try:
        provider_name = os.environ.get("CORTEX_LLM_PROVIDER", "gemini")
        provider = LLMProvider(provider=provider_name) 
    except Exception as e:
        print(f"❌ Error al inicializar LLMProvider: {e}")
        sys.exit(1)
        
    print(f"   ► Conectando cerebro arquitectónico ({provider.model})...")
    
    prompt = CortexPrompt(
        system_instruction=HEALING_SYSTEM_PROMPT,
        working_memory=[{"role": "user", "content": f"Por favor, purga la estática de este archivo:\n\n{original_code}"}],
        temperature=0.1,  # Bajo para mayor determinismo en código
        max_tokens=8192,  # Alto para permitir archivos largos
    )
    
    try:
        healed_code = await provider.invoke(prompt)
        
        # Limpiar posibles bloques markdown si el modelo decide ser rebelde
        if healed_code.startswith("```python"):
            healed_code = healed_code.split("\n", 1)[1]
        if healed_code.startswith("```"):
            healed_code = healed_code.split("\n", 1)[1]
        if healed_code.endswith("```"):
            healed_code = healed_code.rsplit("\n", 1)[0]
            
        # Re-escribir el archivo in-situ
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(healed_code.strip() + "\n")
            
        print(f"✅ ¡Sanación completada! El archivo {filepath.name} ha sido reconstruido.\n")
        print("💡 [SOVEREIGN TIP] Revisa los cambios (`git diff`) e intenta tu commit de nuevo.")
        
    except Exception as e:
        import traceback
        print(f"❌ Fallo crítico durante el Healer:")
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        await provider.close()

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 scripts/auto_healer.py <archivo.py>")
        sys.exit(1)
        
    target_file = Path(sys.argv[1]).resolve()
    asyncio.run(auto_heal(target_file))

if __name__ == "__main__":
    main()
