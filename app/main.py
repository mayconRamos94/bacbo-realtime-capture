import asyncio
from app.websocket.client import start_websocket
from app.storage.database import init_db

async def main():
    await init_db()
    await start_websocket()

if __name__ == "__main__":
    asyncio.run(main())
