"""
ws_client.py — WebSocket poller com auto-recovery real 24h/dia

Fluxo de resiliência:
  1. Tenta reconectar normalmente até MAX_RECONNECT_ATTEMPTS
  2. Se passar do limite → entra em modo RECOVERY:
       - Para de bater cabeça na URL atual
       - Aguarda o mitmproxy capturar uma URL NOVA (até WAIT_FOR_NEW_WS_TIMEOUT)
       - Se chegar nova URL → reconecta imediatamente, zera contadores
       - Se timeout → tenta mais uma vez com a URL atual e reinicia o ciclo
  3. Backoff exponencial com jitter entre tentativas normais
  4. URLWatcher em background notifica nova URL instantaneamente
  5. Health log a cada 5 min confirma que está vivo
  6. Snapshot detalhado quando entra em recovery
"""

import asyncio
import time
import ssl
import random
import sys
from typing import Optional

import websockets
from websockets.exceptions import ConnectionClosed, InvalidURI, InvalidHandshake

from app.domain.event_processor import EventProcessor
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ─── Tunables ────────────────────────────────────────────────────────────────
MAX_RECONNECT_ATTEMPTS  = 5     # tentativas antes de entrar em recovery
WAIT_FOR_NEW_WS_TIMEOUT = 60    # segundos aguardando nova URL no recovery
RECONNECT_BASE          = 2     # backoff base (segundos)
RECONNECT_MAX           = 30    # teto do backoff entre tentativas normais
RECONNECT_JITTER        = 0.3   # ±30% de variação aleatória
HEARTBEAT_TIMEOUT       = 45    # segundos sem mensagem → reconectar
SILENCE_ALARM           = 120   # segundos sem RESULT → logar alerta
WS_URL_POLL_INTERVAL    = 2     # intervalo do watcher de URL
HEALTH_LOG_INTERVAL     = 300   # segundos entre health logs


def _mask_url(url: Optional[str]) -> str:
    if not url:
        return "<vazia>"
    if "?" in url:
        base, qs = url.split("?", 1)
        preview = qs[:25] + "..." if len(qs) > 25 else qs
        return f"{base}?{preview}"
    return url


def _get_ws_url() -> Optional[str]:
    try:
        with open("ws_url.txt", encoding="utf-8") as f:
            url = f.read().strip()
            return url if url else None
    except FileNotFoundError:
        return None
    except Exception as e:
        logger.warning(f"[URL] Erro lendo ws_url.txt: {e}")
        return None


def _backoff(attempt: int) -> float:
    base   = min(RECONNECT_BASE * (2 ** attempt), RECONNECT_MAX)
    jitter = base * RECONNECT_JITTER * (random.random() * 2 - 1)
    return max(1.0, base + jitter)


def _fmt_since(ts: Optional[float]) -> str:
    if ts is None:
        return "nunca recebido"
    return f"{time.time() - ts:.0f}s atrás"


def _fmt_uptime(start: float) -> str:
    h, rem = divmod(int(time.time() - start), 3600)
    m, s   = divmod(rem, 60)
    return f"{h:02d}h{m:02d}m{s:02d}s"


def _log_snapshot(
    ws_url: Optional[str],
    reconnect_attempts: int,
    next_delay: float,
    last_result_at: Optional[float],
    uptime_start: float,
    mode: str,
):
    logger.warning(
        f"\n[SNAPSHOT] {'═' * 48}\n"
        f"  Modo         : {mode}\n"
        f"  Uptime       : {_fmt_uptime(uptime_start)}\n"
        f"  URL ativa    : {_mask_url(ws_url)}\n"
        f"  Tentativas   : {reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS}\n"
        f"  Próx. delay  : {next_delay:.1f}s\n"
        f"  Último RESULT: {_fmt_since(last_result_at)}\n"
        f"[SNAPSHOT] {'═' * 48}"
    )


# ─── URLWatcher ──────────────────────────────────────────────────────────────

class URLWatcher:
    """
    Monitora ws_url.txt em background.
    Quando o mitmproxy grava uma URL nova, notifica via asyncio.Event.
    """

    def __init__(self):
        self.current_url: Optional[str] = None
        self.loaded_at:   Optional[float] = None
        self._running = True
        self.changed  = asyncio.Event()  # setado sempre que URL mudar

    async def run(self):
        while self._running:
            url = _get_ws_url()
            if url and url != self.current_url:
                old = self.current_url
                self.current_url = url
                self.loaded_at   = time.time()
                logger.info(
                    f"[URL] {'Primeira URL capturada' if old is None else 'URL renovada pelo mitmproxy'}: "
                    f"{_mask_url(url)}"
                    + (f"  (substituiu: {_mask_url(old)})" if old else "")
                )
                self.changed.set()   # acorda quem estiver aguardando
            await asyncio.sleep(WS_URL_POLL_INTERVAL)

    def clear_changed(self):
        self.changed.clear()

    def stop(self):
        self._running = False


# ─── Recovery ────────────────────────────────────────────────────────────────

async def _recovery_wait(watcher: URLWatcher, bad_url: Optional[str]) -> Optional[str]:
    """
    Entra em modo recovery: aguarda nova URL do mitmproxy.
    Retorna a nova URL se chegar, ou None se timeout.
    """
    logger.error(
        f"[RECOVERY] {MAX_RECONNECT_ATTEMPTS} falhas consecutivas. "
        f"URL atual provavelmente inválida/expirada.\n"
        f"           Aguardando nova sessão do mitmproxy "
        f"(timeout: {WAIT_FOR_NEW_WS_TIMEOUT}s)..."
    )

    watcher.clear_changed()
    start = asyncio.get_event_loop().time()

    while True:
        new_url = watcher.current_url
        if new_url and new_url != bad_url:
            logger.info(
                f"[RECOVERY] Nova sessão detectada! "
                f"Reconectando com URL renovada: {_mask_url(new_url)}"
            )
            return new_url

        elapsed = asyncio.get_event_loop().time() - start
        remaining = WAIT_FOR_NEW_WS_TIMEOUT - elapsed

        if remaining <= 0:
            logger.warning(
                f"[RECOVERY] Timeout de {WAIT_FOR_NEW_WS_TIMEOUT}s atingido "
                "sem nova URL. Tentando novamente com a URL atual..."
            )
            return None

        # acorda imediatamente se URL mudar, senão verifica a cada 1s
        try:
            await asyncio.wait_for(
                asyncio.shield(watcher.changed.wait()),
                timeout=min(1.0, remaining),
            )
            watcher.clear_changed()
        except asyncio.TimeoutError:
            pass


# ─── Loop principal ───────────────────────────────────────────────────────────

async def start_websocket():
    """
    Poller principal — roda 24h sem intervenção humana.

    Estados:
      NORMAL   → tenta reconectar com backoff até MAX_RECONNECT_ATTEMPTS
      RECOVERY → para de tentar, aguarda nova URL do mitmproxy
    """
    processor    = EventProcessor()
    watcher      = URLWatcher()
    uptime_start = time.time()

    reconnect_attempts  = 0
    last_result_at: Optional[float] = None
    last_health_log     = time.time()

    asyncio.create_task(watcher.run())

    logger.info("[SYS] Poller iniciado. Aguardando URL do mitmproxy...")

    # aguarda primeira URL
    while not watcher.current_url:
        logger.info(f"[URL] Nenhuma URL ainda. Aguardando mitmproxy... (poll {WS_URL_POLL_INTERVAL}s)")
        await asyncio.sleep(WS_URL_POLL_INTERVAL)

    while True:

        # ── Health log periódico ──────────────────────────────────────────────
        now = time.time()
        if now - last_health_log >= HEALTH_LOG_INTERVAL:
            logger.info(
                f"[HEALTH] Uptime: {_fmt_uptime(uptime_start)} | "
                f"Último RESULT: {_fmt_since(last_result_at)} | "
                f"Tentativas: {reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS}"
            )
            last_health_log = now

        # ── AUTO-RECOVERY: limite de tentativas atingido ──────────────────────
        if reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
            _log_snapshot(
                ws_url=watcher.current_url,
                reconnect_attempts=reconnect_attempts,
                next_delay=0,
                last_result_at=last_result_at,
                uptime_start=uptime_start,
                mode="RECOVERY — aguardando nova URL",
            )
            new_url = await _recovery_wait(watcher, bad_url=watcher.current_url)
            if new_url:
                # URL nova chegou — zera tudo e conecta
                reconnect_attempts = 0
            else:
                # timeout — zera tentativas e tenta com URL atual
                reconnect_attempts = 0
            continue  # volta ao topo para conectar

        # ── Backoff exponencial entre tentativas normais ───────────────────────
        if reconnect_attempts > 0:
            delay = _backoff(reconnect_attempts)
            logger.info(
                f"[WS] Aguardando {delay:.1f}s antes de reconectar "
                f"(tentativa {reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS})..."
            )
            # acorda cedo se nova URL chegar durante o backoff
            watcher.clear_changed()
            try:
                await asyncio.wait_for(
                    asyncio.shield(watcher.changed.wait()),
                    timeout=delay,
                )
                logger.info("[URL] Nova URL durante backoff — reconectando agora.")
                reconnect_attempts = 0
                watcher.clear_changed()
            except asyncio.TimeoutError:
                pass

        ws_url = watcher.current_url

        # ── Tentar conectar ───────────────────────────────────────────────────
        ssl_ctx = ssl._create_unverified_context()

        try:
            logger.info(
                f"[WS] Conectando (tentativa {reconnect_attempts + 1}/{MAX_RECONNECT_ATTEMPTS}) "
                f"→ {_mask_url(ws_url)}"
            )

            async with websockets.connect(
                ws_url,
                ssl=ssl_ctx,
                ping_interval=25,
                ping_timeout=20,
                open_timeout=15,
                max_size=2 ** 23,
            ) as ws:

                logger.info(f"[WS] Conexão estabelecida ✓ | Uptime: {_fmt_uptime(uptime_start)}")
                reconnect_attempts = 0   # sucesso — zera contador
                watcher.clear_changed()

                # ── Loop de recebimento ───────────────────────────────────────
                while True:

                    # nova URL enquanto conectado → troca sem esperar queda
                    if watcher.changed.is_set():
                        logger.info(
                            "[URL] Nova URL capturada enquanto conectado — "
                            "reconectando para usar sessão mais recente."
                        )
                        watcher.clear_changed()
                        break

                    # alerta de silêncio longo (não força reconexão)
                    if last_result_at and (time.time() - last_result_at) > SILENCE_ALARM:
                        logger.warning(
                            f"[WS] Servidor silencioso há "
                            f"{time.time() - last_result_at:.0f}s "
                            "(conexão ativa mas sem RESULT)"
                        )

                    try:
                        message = await asyncio.wait_for(
                            ws.recv(),
                            timeout=HEARTBEAT_TIMEOUT,
                        )
                        await processor.process_event(message)
                        last_result_at = time.time()

                    except asyncio.TimeoutError:
                        logger.warning(
                            f"[WS] Heartbeat timeout ({HEARTBEAT_TIMEOUT}s) | "
                            f"Último RESULT: {_fmt_since(last_result_at)}"
                        )
                        reconnect_attempts += 1
                        break

                    except ConnectionClosed as e:
                        code   = e.rcvd.code   if e.rcvd else "N/A"
                        reason = (e.rcvd.reason or "sem razão") if e.rcvd else "sem razão"
                        logger.warning(
                            f"[WS] Conexão fechada — code={code} reason='{reason}' | "
                            f"Último RESULT: {_fmt_since(last_result_at)}"
                        )
                        reconnect_attempts += 1
                        break

        except (InvalidURI, InvalidHandshake) as e:
            logger.error(f"[WS] URL/handshake inválido — {e}")
            reconnect_attempts += 1

        except ConnectionClosed as e:
            code   = e.rcvd.code   if e.rcvd else "N/A"
            reason = (e.rcvd.reason or "sem razão") if e.rcvd else "sem razão"
            logger.error(f"[WS] Falha no handshake — code={code} reason='{reason}'")
            reconnect_attempts += 1

        except OSError as e:
            logger.error(f"[WS] Erro de rede: {e}")
            reconnect_attempts += 1

        except Exception as e:
            logger.exception(f"[WS] Erro inesperado: {e}")
            reconnect_attempts += 1
