import asyncio

from dotenv import load_dotenv

from cortex.skills.autodidact.actuator import daemon_ingesta_soberana

load_dotenv()


async def main():
    import os
    os.environ["CORTEX_LLM_PROVIDER"] = "gemini"
    os.environ["CORTEX_LLM_MODEL"] = "gemini-3.1-pro"
    url = "https://en.wikipedia.org/wiki/Gut%E2%80%93brain_axis"
    intent = "Ingest the Gut-Brain axis knowledge, specifically relating to neurodegenerative disease onset."
    print(f"Running autodidact on: {url} using {os.environ['CORTEX_LLM_PROVIDER']}")
    result = await daemon_ingesta_soberana(url, intent=intent, force_bypass=True)
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
