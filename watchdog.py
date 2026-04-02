"""
watchdog.py — Guarda-cão para Windows

Garante que o bacbo poller fique rodando 24h mesmo se:
  - o processo morrer por crash inesperado
  - o Python lançar uma exceção não capturada no nível do asyncio
  - o SO matar o processo por falta de memória (raro)

Uso:
    python watchdog.py

Isso substitui o "python main.py" no seu start.
"""

import subprocess
import sys
import time
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WATCHDOG] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("watchdog.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

RESTART_DELAY   = 5    # segundos antes de reiniciar
MAX_FAST_DEATHS = 5    # mortes rápidas consecutivas antes de aumentar delay
FAST_DEATH_SECS = 30   # "morte rápida" = morreu em menos de 30s
SLOW_DELAY      = 60   # delay após muitas mortes rápidas consecutivas


def run():
    fast_deaths = 0

    log.info("Watchdog iniciado. Iniciando bacbo poller...")

    while True:
        start = time.time()
        started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log.info(f"[START] Iniciando processo às {started_at}")

        proc = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

        try:
            proc.wait()
        except KeyboardInterrupt:
            log.info("[STOP] Interrompido pelo usuário. Encerrando processo filho...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            log.info("[STOP] Encerrado com sucesso.")
            break

        elapsed = time.time() - start
        exit_code = proc.returncode

        log.warning(
            f"[EXIT] Processo encerrou após {elapsed:.0f}s "
            f"com código {exit_code}"
        )

        if elapsed < FAST_DEATH_SECS:
            fast_deaths += 1
            log.warning(f"[WARN] Morte rápida #{fast_deaths}")
        else:
            fast_deaths = 0

        if fast_deaths >= MAX_FAST_DEATHS:
            delay = SLOW_DELAY
            log.error(
                f"[WARN] {fast_deaths} mortes rápidas consecutivas. "
                f"Aguardando {delay}s antes de reiniciar (pode haver erro de configuração)."
            )
        else:
            delay = RESTART_DELAY

        log.info(f"[RESTART] Reiniciando em {delay}s...")
        time.sleep(delay)


if __name__ == "__main__":
    run()
