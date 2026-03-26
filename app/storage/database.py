import asyncpg

DB_CONFIG = {
    "user": "postgres",
    "password": "postgres",
    "database": "bacbo",
    "host": "localhost",
    "port": 5440
}

pool = None

pool = None

async def init_db():
    global pool
    pool = await asyncpg.create_pool(**DB_CONFIG)

    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)