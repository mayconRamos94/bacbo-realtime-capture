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
                """
                INSERT INTO events (data, winner, player_score, banker_score, event_timestamp)
                VALUES ($1::jsonb, $2, $3, $4, $5)
                ON CONFLICT DO NOTHING
                """,
                json.dumps(data),
                data.get("winner"),
                data.get("playerScore"),
                data.get("bankerScore"),
                data.get("timestamp")
            )

        logger.info("Event saved successfully")

        if ENDPOINT_URL:
            await send_to_endpoint(data)

    except Exception:
        logger.exception("Error saving event")