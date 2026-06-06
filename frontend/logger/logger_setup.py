# frontend\logger\logger_setup.py
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger():
    Path("logs").mkdir(exist_ok=True)

    file_handler = RotatingFileHandler(
        "logs/frontend.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            file_handler,
        ],
    )

    logger = logging.getLogger("frontend")
    return logger
