import asyncio
import websockets
from app.processor.event_processor import process_event
from app.utils.logger import log

WS_URL = "wss://atlasbr.evo-games.com/public/bacbo/player/game/PorBacBo00000001/socket?messageFormat=json&EVOSESSIONID=tut2cyqzqu6bj5dktuu7jk6k4tec6ztr39af0376596f882032bafd85d06f3b5a3a6c673eada50860&client_version=6.20260326.73542.60686-721617f594-r2&instance=syi4tt-tut2cyqzqu6bj5dk-PorBacBo00000001"

RECONNECT_DELAY = 5
HEARTBEAT_TIMEOUT = 10

async def start_websocket():
    while True:
        try:
            log("Conectando ao WebSocket...")

            async with websockets.connect(
                WS_URL,
                ping_interval=5,
                ping_timeout=10
            ) as ws:
                log("Conectado! Iniciando captura de eventos...")

                while True:
                    try:
                        message = await asyncio.wait_for(
                            ws.recv(),
                            timeout=HEARTBEAT_TIMEOUT
                        )

                        process_event(message)

                    except asyncio.TimeoutError:
                        log("Heartbeat não recebido. Conexão possivelmente interrompida.")
                        break

        except Exception as e:
            log(f"Erro na conexão: {e}")

        log(f"Reconectando automaticamente em {RECONNECT_DELAY}s...")
        await asyncio.sleep(RECONNECT_DELAY)