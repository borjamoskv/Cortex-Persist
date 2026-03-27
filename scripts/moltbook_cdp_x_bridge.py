#!/usr/bin/env python3
"""
Moltbook Claim X/Twitter CDP Bridge.
Requirements: Playwright must be installed. Chrome must be running with --remote-debugging-port=9222.
"""
import asyncio
import logging
import sys

from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("moltbook_cdp_bridge")

async def inject_verification_tweet(claim_token: str):
    verification_text = f"Moltbook Verification: {claim_token}"
    logger.info(f"CDP Bridge activated to post: '{verification_text}'")
    
    async with async_playwright() as p:
        try:
            logger.info("Attaching to local Chrome on port 9222...")
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = await context.new_page()
            
            logger.info("Navigating to x.com/compose/tweet...")
            await page.goto("https://x.com/compose/tweet", wait_until="networkidle")
            
            # Wait for DraftEditor or Tweet box
            editor_selector = '[data-testid="tweetTextarea_0"]'
            await page.wait_for_selector(editor_selector, timeout=10000)
            await page.click(editor_selector)
            
            logger.info("Typing verification string...")
            await page.keyboard.type(verification_text, delay=50)
            await page.wait_for_timeout(1000)
            
            # Click the post button
            post_button = '[data-testid="tweetButton"]'
            await page.click(post_button)
            
            logger.info("Tweet injected successfully.")
            await page.wait_for_timeout(3000)
            
            await page.close()
            logger.info("CDP execution complete. Structural constraint passed.")
            
        except Exception as e:
            logger.error(f"CDP Bridge execution failed: {e}")
            raise

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python moltbook_cdp_x_bridge.py <moltbook_claim_token>")
        sys.exit(1)
        
    token = sys.argv[1]
    asyncio.run(inject_verification_tweet(token))
