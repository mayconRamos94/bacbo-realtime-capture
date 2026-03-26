import asyncio

from app.capture.ws_client import start_websocket
from app.storage.database import init_db, close_db
from app.utils.logger import setup_logger, get_logger

# garante carregamento e validação do .env
from app.config import settings


logger = get_logger(__name__)


async def main():
    logger.info("Starting BacBo service...")

    try:
        logger.info("Initializing database...")
        await init_db()

        logger.info("Starting WebSocket client...")
        await start_websocket()

    except Exception:
        logger.exception("Application error")
        raise

    finally:
        logger.info("Shutting down application...")
        await close_db()


if __name__ == "__main__":
    setup_logger()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")