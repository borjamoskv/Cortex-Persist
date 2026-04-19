import httpx
import asyncio
import os

async def bridge():
    url = "http://localhost:8000/fuzz/stream"
    print(f"SUPER YOLO BRIDGE: Conectando a {url}...")
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", url) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        # Extraer data y persistir en buffer para el motor de cine
                        with open("telemetry_buffer.txt", "a") as f:
                            f.write(line[5:] + "\n")
                        # Rotación simple de buffer (mantener solo últimas 10 líneas)
                        with open("telemetry_buffer.txt", "r") as f:
                            lines = f.readlines()
                        if len(lines) > 20:
                            with open("telemetry_buffer.txt", "w") as f:
                                f.writelines(lines[-20:])
    except Exception as e:
        print(f"BRIDGE_FAIL: {e}. Usando telemetría sintética (Random Hex).")

if __name__ == "__main__":
    asyncio.run(bridge())
