import json
import asyncio
from app.storage.saver import save
from app.utils.logger import log

# 🔥 controle de duplicidade
last_timestamp = None

def process_event(raw_message):
    global last_timestamp

    try:
        data = json.loads(raw_message)

        event_type = data.get("type")
        log(f"Evento recebido: {event_type}")

        # 🔥 só processa evento relevante
        if event_type != "bacbo.road":
            return

        timestamp = data.get("time")

        # 🔥 evita duplicados
        if timestamp == last_timestamp:
            return

        last_timestamp = timestamp

        history = data.get("args", {}).get("history", [])
        if not history:
            return

        last = history[-1]

        result_data = {
            "type": "result",
            "winner": last.get("winner"),
            "playerScore": last.get("playerScore"),
            "bankerScore": last.get("bankerScore"),
            "timestamp": timestamp
        }

        # 🔥 log profissional
        log(
            f"RESULTADO -> {result_data['winner']} | "
            f"P:{result_data['playerScore']} vs B:{result_data['bankerScore']}"
        )

        asyncio.create_task(save(result_data))

    except Exception as e:
        log(f"Erro ao processar evento: {e}")