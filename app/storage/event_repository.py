import aiohttp
import json

from app.storage.database import get_pool
from app.utils.logger import get_logger
from app.config.settings import ENDPOINT_URL


logger = get_logger(__name__)


async def send_to_endpoint(data: dict):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(ENDPOINT_URL, json=data) as response:
                if response.status >= 400:
                    logger.error(f"Endpoint error: {response.status}")
    except Exception:
        logger.exception("Error sending to endpoint")


async def save_event(data: dict):
    try:
        logger.info("Saving event...")

        pool = get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO events (data) VALUES ($1::jsonb)",
                json.dumps(data)
            )

        logger.info("Event saved successfully")

        # 🔥 só envia se estiver configurado
        if ENDPOINT_URL:
            await send_to_endpoint(data)

    except Exception:
        logger.exception("Error saving event")