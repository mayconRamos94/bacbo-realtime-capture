import json
import asyncio

from app.storage.event_repository import save_event
from app.utils.logger import get_logger


logger = get_logger(__name__)


class EventProcessor:

    def __init__(self):
        # controle correto de duplicidade
        self._last_event = None

    async def process_event(self, raw_message: str):
        try:
            data = json.loads(raw_message)

            event_type = data.get("type")

            # processa apenas eventos relevantes
            if event_type != "bacbo.road":
                return

            timestamp = data.get("time")

            history = data.get("args", {}).get("history", [])
            if not history:
                return

            last = history[-1]

            result_data = self._build_result(last, timestamp)

            # validação mínima
            if not result_data["winner"]:
                logger.warning("Invalid event data (missing winner)")
                return

            # chave de deduplicação baseada no conteúdo
            current_event = (
                result_data["winner"],
                result_data["playerScore"],
                result_data["bankerScore"]
            )

            # evita duplicados reais
            if current_event == self._last_event:
                return

            self._last_event = current_event

            logger.info(
                f"RESULT -> {result_data['winner']} | "
                f"P:{result_data['playerScore']} vs B:{result_data['bankerScore']}"
            )

            # não bloqueia, mas com controle
            asyncio.create_task(self._safe_save(result_data))

        except Exception:
            logger.exception("Error processing event")

    async def _safe_save(self, data: dict):
        try:
            await save_event(data)
        except Exception:
            logger.exception("Error in background save task")

    def _build_result(self, last: dict, timestamp):
        return {
            "type": "result",
            "winner": last.get("winner"),
            "playerScore": last.get("playerScore"),
            "bankerScore": last.get("bankerScore"),
            "timestamp": timestamp
        }