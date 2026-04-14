import base64
import json
import logging
from typing import Any, Optional

import httpx
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
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

    async def connect(self, target_url_substring: str = "") -> bool:
        """Connect to an active Chrome/Edge tab via CDP."""
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.base_url}/json")
                res.raise_for_status()
                tabs = res.json()

            # Find matching tab
            target = None
            for tab in tabs:
                if tab.get("type") == "page" and target_url_substring in tab.get("url", ""):
                    target = tab
                    break

            if not target:
                logger.error("No tab found matching: '%s'", target_url_substring)
                return False

            self.ws_url = target["webSocketDebuggerUrl"]
            self.ws = await websockets.connect(self.ws_url)
            logger.info("Connected to CDP: %s", target["url"])

            # Enable core domains
            await self.send("Page.enable")
            await self.send("Runtime.enable")
            return True
        except Exception as e:
            logger.error("Connection failed: %s", e)
            return False

    async def send(self, method: str, params: dict = None) -> Any:
        """Send a raw CDP command."""
        self.msg_id += 1
        payload = {"id": self.msg_id, "method": method, "params": params or {}}
        await self.ws.send(json.dumps(payload))
        while True:
            res_str = await self.ws.recv()
            res = json.loads(res_str)
            # CDP can send asynchronous events without 'id', wait for our response
            if res.get("id") == self.msg_id:
                # Check if it's an error response
                if "error" in res:
                    logger.error("CDP Error in %s: %s", method, res["error"])
                return res.get("result", {})

    async def extract_selector(self, selector: str, extract_html: bool = False) -> Optional[str]:
        """Extract text or HTML content from a CSS selector."""
        prop = "outerHTML" if extract_html else "innerText"
        js = f"document.querySelector('{selector}').{prop}"
        return await self.evaluate(js)

    async def extract_page(self, extract_html: bool = False) -> Optional[str]:
        """Extract entire page text or HTML."""
        prop = "outerHTML" if extract_html else "innerText"
        js = f"document.documentElement.{prop}"
        return await self.evaluate(js)

    async def click(self, selector: str):
        """Perform a click on a CSS selector."""
        js = f"document.querySelector('{selector}').click()"
        await self.evaluate(js)

    async def type_text(self, selector: str, text: str):
        """Perform a type action on a CSS selector by synthesizing events."""
        # Sanitize text for JS literal injection
        safe_text = text.replace('"', '\\"').replace("\n", "\\n")
        js = f'''
            let el = document.querySelector("{selector}");
            if (el) {{
                el.focus();
                el.value = "{safe_text}";
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        '''
        await self.evaluate(js)

    async def evaluate(self, js_expression: str) -> Any:
        """Evaluate raw JS and return the result."""
        res = await self.send(
            "Runtime.evaluate", {"expression": js_expression, "returnByValue": True}
        )
        if "result" in res and "value" in res["result"]:
            return res["result"]["value"]

        # Check for exception details
        if "exceptionDetails" in res:
            logger.error("JS Error: %s", res["exceptionDetails"])

        return None

    async def screenshot(self, filepath: str):
        """Capture a screenshot of the page."""
        res = await self.send("Page.captureScreenshot", {"format": "png"})
        if "data" in res:
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(res["data"]))
            logger.info("Screenshot saved to %s", filepath)
        else:
            logger.error("Failed to capture screenshot data.")

    async def close(self):
        if self.ws:
            await self.ws.close()
