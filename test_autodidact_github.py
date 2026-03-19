import asyncio
import sys

# Añadir el raíz del proyecto al path para que los imports funcionen
sys.path.append("/Users/borjafernandezangulo/30_CORTEX")

from cortex.extensions.skills.autodidact.actuator import daemon_ingesta_soberana


async def main():
    url = "https://docs.github.com/es"
    intent = "Aprender documentación base de GitHub en español"
    
    print(f"🚀 Iniciando Autovía para: {url}")
    result = await daemon_ingesta_soberana(url, intent=intent, force_bypass=True)
    print(f"✅ Resultado: {result}")

if __name__ == "__main__":
    asyncio.run(main())
