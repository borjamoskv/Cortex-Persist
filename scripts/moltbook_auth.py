import os
import httpx
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class VerifiedAgent:
    id: str
    name: str
    description: str
    karma: int
    is_claimed: bool
    follower_count: int
    stats: Dict[str, Any]
    owner: Optional[Dict[str, Any]] = None

class MoltbookAuthError(Exception):
    """Raised for authentication failures."""
    pass

class MoltbookTokenExpired(MoltbookAuthError):
    """Raised when the identity token is expired."""
    pass

class MoltbookAuth:
    """
    Framework-agnostic Moltbook Authentication Helper.
    CORTEX v5.5 Implementation.
    """
    def __init__(self, app_key: Optional[str] = None):
        self.app_key = app_key or os.environ.get("MOLTBOOK_APP_KEY")
        if not self.app_key:
            raise MoltbookAuthError("MOLTBOOK_APP_KEY not found in environment.")
        
        self.verify_url = "https://www.moltbook.com/api/v1/agents/verify-identity"

    async def verify_request(self, headers: Dict[str, str]) -> VerifiedAgent:
        """
        Extracts and verifies the Moltbook identity token from request headers.
        Header: X-Moltbook-Identity
        """
        token = headers.get("X-Moltbook-Identity")
        if not token:
            raise MoltbookAuthError("Missing X-Moltbook-Identity header.")

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(
                    self.verify_url,
                    headers={"X-Moltbook-App-Key": self.app_key},
                    json={"token": token}
                )
                
                if resp.status_code == 401:
                    raise MoltbookTokenExpired("Token is invalid or expired.")
                
                if resp.status_code != 200:
                    raise MoltbookAuthError(f"Verification failed with status {resp.status_code}: {resp.text}")

                data = resp.json()
                if not data.get("valid"):
                    raise MoltbookAuthError(f"Token is invalid: {data.get('message', 'Unknown error')}")

                agent_data = data.get("agent", {})
                return VerifiedAgent(
                    id=agent_data.get("id"),
                    name=agent_data.get("name"),
                    description=agent_data.get("description"),
                    karma=agent_data.get("karma", 0),
                    is_claimed=agent_data.get("is_claimed", False),
                    follower_count=agent_data.get("follower_count", 0),
                    stats=agent_data.get("stats", {}),
                    owner=agent_data.get("owner")
                )
            except httpx.HTTPError as e:
                logger.error(f"Moltbook Auth connectivity error: {e}")
                raise MoltbookAuthError(f"Could not connect to Moltbook: {e}")

# Simple test runner if executed directly
if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("Testing MoltbookAuth Helper...")
        try:
            # Mocking environment for test
            os.environ["MOLTBOOK_APP_KEY"] = "moltdev_test_key"
            auth = MoltbookAuth()
            print("✅ Helper initialized.")
            
            # This will fail unless a real token is provided
            # try:
            #     await auth.verify_request({"X-Moltbook-Identity": "invalid_token"})
            # except MoltbookAuthError as e:
            #     print(f"✅ Caught expected error: {e}")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")

    asyncio.run(test())
