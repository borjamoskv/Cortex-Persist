import logging
import os
import aiohttp

logger = logging.getLogger("ouroboros.telegram")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

async def notify_human(message: str):
    if not BOT_TOKEN or not CHAT_ID:
        logger.warning(f"Telegram not configured. Message: {message}")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"Failed to send telegram: {text}")
    except Exception as e:
        logger.error(f"Telegram error: {e}")
