"""
auto_refresh.py — Renovação automática de sessão sem extensão de browser

Como funciona:
  1. Monitora ws_url.txt e extrai o token da URL
  2. Se o token ficar sem renovação por TOKEN_MAX_AGE_SECONDS:
     a. Se achar aba do jogo via CDP → recarrega ela (Page.reload)
     b. Se não achar aba do jogo mas CDP ativo → navega aba existente para o jogo (Page.navigate)
     c. Se CDP não disponível → abre nova janela como último recurso
  3. Nunca acumula janelas/abas desnecessárias

Uso:
    python auto_refresh.py
"""

import subprocess
import time
import os
import sys
import logging
import requests
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# ─── Configurações ────────────────────────────────────────────────────────────
TOKEN_MAX_AGE_SECONDS = 20 * 60      # minutos sem novo token → força refresh
CHECK_INTERVAL        = 30          # verifica a cada 30s
GAME_URL              = "https://start.bet.br/live-casino/game/2630915?provider=Evolution&from=%2Flive-casino"
CDP_PORT              = 9222
CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AUTO-REFRESH] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("auto_refresh.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


def _find_chrome() -> str | None:
    for path in CHROME_PATHS:
        if Path(path).exists():
            return path
    return None


def _get_token_from_url(url: str) -> str | None:
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        for param in ["EVOSESSIONID", "sessionId", "token", "sid", "session"]:
            if param in qs:
                return qs[param][0]
        return parsed.query[:60] if parsed.query else None
    except Exception:
        return None


def _read_ws_url() -> str | None:
    try:
        with open("ws_url.txt", encoding="utf-8") as f:
            return f.read().strip() or None
    except FileNotFoundError:
        return None


def _get_all_tabs() -> list:
    try:
        return requests.get(f"http://127.0.0.1:{CDP_PORT}/json", timeout=3).json()
    except Exception:
        return []


def _find_game_tab(tabs: list) -> dict | None:
    for tab in tabs:
        url = tab.get("url", "")
        if "start.bet" in url or "evo-games" in url or "bacbo" in url.lower():
            return tab
    return None


def _find_any_page_tab(tabs: list) -> dict | None:
    """Retorna qualquer aba de página real (não extensão/devtools)."""
    for tab in tabs:
        if tab.get("type") == "page" and not tab.get("url", "").startswith("chrome"):
            return tab
    # fallback: qualquer aba do tipo page
    for tab in tabs:
        if tab.get("type") == "page":
            return tab
    return None


def _cdp_command(ws_debug_url: str, method: str, params: dict = {}) -> bool:
    """Envia comando CDP via WebSocket."""
    try:
        import websocket
        ws = websocket.create_connection(ws_debug_url, timeout=5)
        import json
        ws.send(json.dumps({"id": 1, "method": method, "params": params}))
        ws.close()
        return True
    except Exception as e:
        log.warning(f"Falha no comando CDP ({method}): {e}")
        return False


def _force_refresh(chrome_path: str):
    """
    Estratégia em cascata — nunca abre janela nova se o Chrome já está aberto:
      1. Achou aba do jogo → recarrega (Page.reload)
      2. Não achou aba do jogo mas CDP ativo → navega aba existente para o jogo (Page.navigate)
      3. CDP não disponível → abre nova janela como último recurso
    """
    tabs = _get_all_tabs()

    if tabs:
        # estratégia 1: recarregar aba do jogo
        game_tab = _find_game_tab(tabs)
        if game_tab:
            ws_url = game_tab.get("webSocketDebuggerUrl")
            if ws_url:
                log.info(f"Aba do jogo encontrada — recarregando via CDP...")
                if _cdp_command(ws_url, "Page.reload", {"ignoreCache": True}):
                    log.info("Aba recarregada com sucesso ✓")
                    return

        # estratégia 2: navegar aba existente para o jogo
        any_tab = _find_any_page_tab(tabs)
        if any_tab:
            ws_url = any_tab.get("webSocketDebuggerUrl")
            if ws_url:
                log.info(
                    f"Aba do jogo não encontrada — navegando aba existente para o jogo..."
                )
                if _cdp_command(ws_url, "Page.navigate", {"url": GAME_URL}):
                    log.info("Navegação iniciada via CDP ✓")
                    return

    # estratégia 3: último recurso — abre nova janela
    log.warning("CDP não disponível — abrindo nova janela como fallback...")
    try:
        subprocess.Popen(
            [chrome_path, "--remote-debugging-port=9222", GAME_URL],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log.info("Nova janela aberta.")
    except Exception as e:
        log.error(f"Erro ao abrir Chrome: {e}")


def _ensure_chrome_with_cdp(chrome_path: str) -> bool:
    try:
        requests.get(f"http://127.0.0.1:{CDP_PORT}/json", timeout=2)
        log.info(f"CDP ativo na porta {CDP_PORT} ✓")
        return True
    except Exception:
        log.warning(
            f"Chrome não está rodando com --remote-debugging-port={CDP_PORT}.\n"
            "           Abra o Chrome assim para habilitar CDP:\n"
            f'           Start-Process "{chrome_path}" '
            f'-ArgumentList "--remote-debugging-port={CDP_PORT}"\n'
            "           Sem CDP, o auto-refresh abrirá nova janela como fallback."
        )
        return False


def run():
    chrome = _find_chrome()
    if not chrome:
        log.error("Chrome não encontrado. Edite CHROME_PATHS no auto_refresh.py.")
        sys.exit(1)

    log.info(f"Auto-refresh iniciado | Chrome: {chrome}")
    log.info(f"Renovação forçada se token ficar > {TOKEN_MAX_AGE_SECONDS}s sem mudar")

    _ensure_chrome_with_cdp(chrome)

    last_token    = None
    last_token_at = None
    refresh_count = 0

    while True:
        url = _read_ws_url()

        if url:
            token = _get_token_from_url(url)

            if token != last_token:
                if last_token is not None:
                    age = time.time() - last_token_at if last_token_at else 0
                    log.info(f"Novo token detectado (anterior tinha {age:.0f}s) ✓")
                else:
                    log.info("Primeiro token detectado ✓")
                last_token    = token
                last_token_at = time.time()

            else:
                if last_token_at:
                    age       = time.time() - last_token_at
                    remaining = TOKEN_MAX_AGE_SECONDS - age

                    if remaining <= 0:
                        refresh_count += 1
                        log.warning(
                            f"Token com {age:.0f}s sem renovação — "
                            f"forçando refresh #{refresh_count}..."
                        )
                        _force_refresh(chrome)
                        last_token_at = time.time()
                    elif remaining < 60:
                        log.info(f"Token expira em {remaining:.0f}s — refresh em breve...")
        else:
            log.warning("ws_url.txt não encontrado — aguardando mitmproxy...")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run()
