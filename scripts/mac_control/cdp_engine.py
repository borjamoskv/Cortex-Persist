import asyncio
import json
import logging
import sys
import websockets
import httpx
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mac-control-omega")

class MacControlOmega:
    """Sovereign macOS UI Control via Raw CDP."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 9222):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.ws_url: Optional[str] = None
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.msg_id = 0

    async def connect(self, target_url_substring: str = ""):
        """Connect to an active Chrome/Edge tab via CDP."""
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.base_url}/json")
                res.raise_for_status()
                tabs = res.json()
                
            # Find matching tab
            target = None
            for tab in tabs:
                if tab['type'] == 'page' and target_url_substring in tab['url']:
                    target = tab
                    break
            
            if not target:
                logger.error(f"No tab found matching: {target_url_substring}")
                return False
                
            self.ws_url = target['webSocketDebuggerUrl']
            self.ws = await websockets.connect(self.ws_url)
            logger.info(f"Connected to CDP: {target['url']}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    async def send(self, method: str, params: dict = None) -> Any:
        """Send a raw CDP command."""
        self.msg_id += 1
        payload = {
            "id": self.msg_id,
            "method": method,
            "params": params or {}
        }
        await self.ws.send(json.dumps(payload))
        res = await self.ws.recv()
        return json.loads(res)

    async def extract_selector(self, selector: str) -> Optional[str]:
        """Extract text content from a CSS selector."""
        js = f"document.querySelector('{selector}').innerText"
        res = await self.send("Runtime.evaluate", {"expression": js, "returnByValue": True})
        if 'result' in res and 'value' in res['result']:
            return res['result']['value']
        return None

    async def click(self, selector: str):
        """Perform a click on a CSS selector."""
        js = f"document.querySelector('{selector}').click()"
        await self.send("Runtime.evaluate", {"expression": js})

    async def close(self):
        if self.ws:
            await self.ws.close()

if __name__ == "__main__":
    # Smoke test / usage example
    async def main():
        ctl = MacControlOmega()
        if await ctl.connect("github.com"):
            title = await ctl.extract_selector("title")
            print(f"Tab Title: {title}")
            await ctl.close()
            
    asyncio.run(main())
