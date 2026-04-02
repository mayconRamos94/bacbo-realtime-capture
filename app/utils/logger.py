import logging
import sys
from logging.handlers import RotatingFileHandler


def setup_logger():
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if root.handlers:
        return

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # console
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)

    # arquivo rotativo (10MB x 5) — diagnóstico retroativo
    try:
        fh = RotatingFileHandler(
            "bacbo_poller.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Log em arquivo indisponível: {e}")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
