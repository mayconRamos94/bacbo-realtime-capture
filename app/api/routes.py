from fastapi import APIRouter
from app.storage.database import get_pool
import json

router = APIRouter()


def _get_pool_or_error():
    pool = get_pool()
    if not pool:
        return None, {"error": "Database not initialized"}
    return pool, None


async def _fetch_events(limit: int):
    pool, error = _get_pool_or_error()
    if error:
        return error

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT data FROM events ORDER BY id DESC LIMIT $1",
            limit
        )

    return [json.loads(r["data"]) for r in rows]


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/results")
async def get_results(limit: int = 50):
    return await _fetch_events(limit)


@router.get("/stats")
async def stats(limit: int = 100):
    pool, error = _get_pool_or_error()
    if error:
        return error

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT winner, player_score, banker_score
            FROM events
            ORDER BY id DESC
            LIMIT $1
            """,
            limit
        )

    total = len(rows)
    player = sum(1 for r in rows if r["winner"] == "Player")
    banker = sum(1 for r in rows if r["winner"] == "Banker")

    return {
        "total": total,
        "player": player,
        "banker": banker,
        "player_rate": player / total if total else 0,
        "banker_rate": banker / total if total else 0
    }