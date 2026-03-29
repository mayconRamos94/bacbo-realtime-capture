import asyncio
import websockets
import ssl

from app.domain.event_processor import EventProcessor
from app.utils.logger import get_logger


logger = get_logger(__name__)

RECONNECT_DELAY = 1  # fallback leve
HEARTBEAT_TIMEOUT = 10


def get_ws_url():
    try:
        with open("ws_url.txt") as f:
            return f.read().strip()
    except Exception:
        return None


async def start_websocket():
    processor = EventProcessor()

    while True:
        try:
            ws_url = get_ws_url()

            if not ws_url:
                logger.warning("WS URL not found. Waiting...")
                await asyncio.sleep(3)
                continue

            logger.info(f"Connecting to WebSocket: {ws_url}")

            ssl_context = ssl._create_unverified_context()

            async with websockets.connect(
                ws_url,
                ping_interval=5,
                ping_timeout=10,
                ssl=ssl_context
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
                        logger.warning("Heartbeat timeout. Reconnecting immediately...")
                        break  # 👈 sai instantâneo

                    except websockets.ConnectionClosed:
                        logger.warning("Connection closed. Reconnecting immediately...")
                        break  # 👈 sai instantâneo

        except Exception:
            logger.exception("WebSocket connection error")

        # delay mínimo só pra evitar loop agressivo
        await asyncio.sleep(RECONNECT_DELAY)