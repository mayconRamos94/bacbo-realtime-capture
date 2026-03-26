import aiohttp
import json
from app.storage import database
from app.utils.logger import log

ENDPOINT_URL = "https://sua-api.com/endpoint"

async def send_to_endpoint(data):
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(ENDPOINT_URL, json=data)
    except Exception as e:
        log(f"Erro endpoint: {e}")

async def save(data):
    try:
        log("Salvando evento...")

        if database.pool is None:
            log("Pool ainda não inicializado")
            return

        async with database.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO events (data) VALUES ($1::jsonb)",
                json.dumps(data)  # 🔥 CORREÇÃO AQUI
            )

        log("Evento salvo com sucesso")

        await send_to_endpoint(data)

    except Exception as e:
        log(f"Erro ao salvar: {e}")