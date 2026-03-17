import asyncio

from cortex.skills.autodidact.actuator import daemon_ingesta_soberana


async def main():
    url = "https://developers.cloudflare.com/"
    print(f"Running autodidact on: {url} with Exa bypass included.")
    result = await daemon_ingesta_soberana(
        url, intent="Ingest Cloudflare Developers documentation", force_bypass=True
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
