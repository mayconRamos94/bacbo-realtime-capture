import asyncpg

from app.config.settings import DATABASE_URL
from app.utils.logger import get_logger


logger = get_logger(__name__)

_pool: asyncpg.Pool | None = None


async def init_db():
    global _pool

    if _pool is not None:
        return

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

            await conn.execute("""
                ALTER TABLE events
                ADD COLUMN IF NOT EXISTS winner TEXT,
                ADD COLUMN IF NOT EXISTS player_score INT,
                ADD COLUMN IF NOT EXISTS banker_score INT,
                ADD COLUMN IF NOT EXISTS event_timestamp BIGINT
            """)

            await conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS unique_event_idx
                ON events (winner, player_score, banker_score)
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