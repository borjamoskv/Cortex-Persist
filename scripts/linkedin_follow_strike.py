#!/usr/bin/env python3
"""
LinkedIn Follow Strike Agent v1.0.0
Agentic Strike on AI Agents companies/people.
Industrial Noir / CORTEX Persist Integration.
"""

import sys
import time
import random
import asyncio
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext, Page

# CONFIGURATION
TARGET_URL = "https://www.linkedin.com/search/results/companies/?keywords=ai%20agents&origin=CLUSTER_EXPANSION&spellCorrectionEnabled=true&page=6"
FOLLOW_LIMIT = 200
THERMODYNAMIC_DELAY_RANGE = (4, 12)  # Delay between follows in seconds
SCROLL_DELAY_RANGE = (1, 3) 
USER_DATA_DIR = Path.home() / ".cortex/linkedin_agent_profile"

class CortexLogger:
    @staticmethod
    def log(message: str, type: str = "info"):
        """Logs to CORTEX Persist ledger via CLI"""
        content = f"[{type.upper()}] {message}"
        try:
            subprocess.run(
                ["cortex", "memory", "store", "--agent", "linkedin-follow-strike", "--content", content],
                capture_output=True, text=True
            )
            print(f"∴ CORTEX: {content}")
        except Exception as e:
            print(f"!!! CORTEX LOG FAIL: {e}")

class LinkedInFollowStrike:
    def __init__(self, limit: int = 200):
        self.limit = limit
        self.count = 0
        self.logger = CortexLogger()

    async def human_delay(self, duration_range=THERMODYNAMIC_DELAY_RANGE):
        delay = random.uniform(*duration_range)
        await asyncio.sleep(delay)

    async def scroll_slowly(self, page: Page):
        """Scroll down to simulate human browsing and trigger lazy loading"""
        for _ in range(3):
            await page.mouse.wheel(0, 400 + random.randint(-100, 100))
            await self.human_delay(SCROLL_DELAY_RANGE)

    async def run(self, url: str):
        async with async_playwright() as p:
            # Create user data dir if it doesn't exist
            USER_DATA_DIR.parent.mkdir(parents=True, exist_ok=True)
            
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(USER_DATA_DIR),
                headless=False,  # Headless=False is safer for LinkedIn session management and user feedback
                args=["--start-maximized", "--no-sandbox"]
            )
            
            page = context.pages[0]
            await page.goto(url)
            
            self.logger.log(f"Launched Strike on {url}", "genesis")

            while self.count < self.limit:
                # 1. Check if logged in / Check for login wall
                if await page.query_selector('form.login__form'):
                    self.logger.log("Login required. Waiting for human interaction...", "alert")
                    # Wait for user to log in manually in the opened window
                    await page.wait_for_selector('.reusable-search__result-container', timeout=0)
                    self.logger.log("Login detected. Resuming Strike.", "recovery")

                # 2. Wait for results
                await page.wait_for_selector('.reusable-search__result-container', timeout=30000)
                await self.scroll_slowly(page)

                # 3. Find follow buttons
                # Targets both 'Seguir' (ES) and 'Follow' (EN)
                buttons = await page.query_selector_all('button[aria-label^="Seguir"], button[aria-label^="Follow"]')
                
                self.logger.log(f"Found {len(buttons)} entities on current page.", "scan")

                for btn in buttons:
                    if self.count >= self.limit:
                        break

                    label = await btn.get_attribute("aria-label")
                    btn_text = await btn.inner_text()
                    
                    # Logic: Avoid clicking if already following or if it's 'En espera' (Pending)
                    if any(x in btn_text.lower() for x in ["siguiendo", "en espera", "following", "pending"]):
                        continue

                    try:
                        # Humanity Check: Move mouse to button before clicking
                        await btn.hover()
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                        
                        await btn.click()
                        self.count += 1
                        
                        self.logger.log(f"Followed: {label} ({self.count}/{self.limit})", "victory")
                        
                        # Cool down
                        await self.human_delay()
                    except Exception as e:
                        self.logger.log(f"Failed to click button {label}: {e}", "error")

                # 4. Next Page logic
                if self.count < self.limit:
                    next_btn = await page.query_selector('button[aria-label="Siguiente"], button[aria-label="Next"]')
                    if next_btn:
                        self.logger.log("Advancing to next page...", "navigation")
                        await next_btn.click()
                        await asyncio.sleep(5)  # Wait for page load
                    else:
                        self.logger.log("No more pages available. Strike complete.", "end")
                        break

            await context.close()
            self.logger.log(f"Strike finalized. Total followers added: {self.count}", "final")

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else TARGET_URL
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else FOLLOW_LIMIT
    
    agent = LinkedInFollowStrike(limit=limit)
    asyncio.run(agent.run(url))
