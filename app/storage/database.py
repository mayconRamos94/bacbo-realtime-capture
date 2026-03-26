import asyncpg

from app.config.settings import DATABASE_URL
from app.utils.logger import get_logger


logger = get_logger(__name__)

_pool: asyncpg.Pool | None = None


async def init_db():
    global _pool

    if _pool is not None:
        return  # evita recriar pool

    try:
        logger.info("Initializing database connection pool...")

        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=10
        )

        async with _pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id SERIAL PRIMARY KEY,
                    data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

        logger.info("Database initialized successfully")

    except Exception:
        logger.exception("Failed to initialize database")
        raise


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _pool


async def close_db():
    global _pool

    if _pool:
        await _pool.close()
        logger.info("Database pool closed")
        _pool = None