import asyncio
from cortex.moltbook.client import MoltbookClient
from pathlib import Path

async def main():
    creds_path = Path('/Users/borjafernandezangulo/.config/moltbook/credentials.json')
    client = MoltbookClient(credentials_path=creds_path)
    status = await client.check_status()
    print(status)
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
