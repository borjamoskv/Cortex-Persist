import httpx
import secrets
import string
import asyncio
from typing import Optional, List, Dict

class TempMail:
    """
    Sovereign Temporal Email Engine via Mail.tm API.
    Used for automated agent registration and verification.
    """
    API_URL = "https://api.mail.tm"

    def __init__(self):
        self._client = httpx.AsyncClient(base_url=self.API_URL, timeout=30.0)
        self.address: Optional[str] = None
        self.password: Optional[str] = None
        self.token: Optional[str] = None
        self.account_id: Optional[str] = None

    async def create_account(self) -> str:
        """Creates a random account and returns the email address."""
        # 1. Get domain
        resp = await self._client.get("/domains")
        domain = resp.json()["hydra:member"][0]["domain"]

        # 2. Generate random address and pass
        random_str = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(10))
        self.address = f"{random_str}@{domain}"
        self.password = secrets.token_urlsafe(12)

        # 3. Create
        resp = await self._client.post("/accounts", json={
            "address": self.address,
            "password": self.password
        })
        resp.raise_for_status()
        self.account_id = resp.json()["id"]

        # 4. Get token
        resp = await self._client.post("/token", json={
            "address": self.address,
            "password": self.password
        })
        resp.raise_for_status()
        self.token = resp.json()["token"]
        self._client.headers["Authorization"] = f"Bearer {self.token}"

        return self.address

    async def get_messages(self) -> List[Dict]:
        """Fetches messages for the current account."""
        resp = await self._client.get("/messages")
        resp.raise_for_status()
        return resp.json()["hydra:member"]

    async def wait_for_message(self, timeout: int = 60, interval: int = 5) -> Optional[Dict]:
        """Polls for the first message."""
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < timeout:
            msgs = await self.get_messages()
            if msgs:
                # Get full message content
                msg_id = msgs[0]["id"]
                resp = await self._client.get(f"/messages/{msg_id}")
                return resp.json()
            await asyncio.sleep(interval)
        return None

    async def close(self):
        await self._client.aclose()
