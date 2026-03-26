import asyncio
import websockets

from app.domain.event_processor import EventProcessor
from app.utils.logger import get_logger
from app.config.settings import WS_URL


logger = get_logger(__name__)

RECONNECT_DELAY = 5
HEARTBEAT_TIMEOUT = 10


async def start_websocket():
    processor = EventProcessor()

    while True:
        try:
            logger.info("Connecting to WebSocket...")

            async with websockets.connect(
                WS_URL,
                ping_interval=5,
                ping_timeout=10
            ) as ws:

                logger.info("Connected. Listening for events...")

                while True:
                    try:
                        message = await asyncio.wait_for(
                            ws.recv(),
                            timeout=HEARTBEAT_TIMEOUT
                        )

                        await processor.process_event(message)

                    except asyncio.TimeoutError:
                        logger.warning("Heartbeat timeout. Reconnecting...")
                        break

                    except websockets.ConnectionClosed:
                        logger.warning("Connection closed. Reconnecting...")
                        break

        except Exception:
            logger.exception("WebSocket connection error")

        logger.info(f"Reconnecting in {RECONNECT_DELAY}s...")
        await asyncio.sleep(RECONNECT_DELAY)