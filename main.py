from fastapi import FastAPI
import uvicorn
import asyncio

from app.api.routes import router as api_router
from app.capture.ws_client import start_websocket
from app.storage.database import init_db, close_db
from app.utils.logger import setup_logger, get_logger

from app.config import settings

logger = get_logger(__name__)

app = FastAPI()
app.include_router(api_router)


async def start_api():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    logger.info("Starting BacBo service...")

    try:
        logger.info("Initializing database...")
        #await init_db()

        logger.info("Starting services (WebSocket + API)...")

        await asyncio.gather(
            start_websocket(),  # 👈 aqui está o segredo
            start_api()
        )

    except Exception:
        logger.exception("Application error")
        raise

    finally:
        logger.info("Shutting down application...")
        #await close_db()


if __name__ == "__main__":
    setup_logger()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")