# frontend\logger\logger_setup.py
import logging

from logging.handlers import RotatingFileHandler
from pathlib import Path

print(Path.cwd())


def setup_logger():
    BASE_DIR = Path(__file__).resolve().parent.parent
    LOG_DIR = BASE_DIR / "logs"

    LOG_DIR.mkdir(exist_ok=True)

    file_handler = RotatingFileHandler(
        LOG_DIR / "logs/frontend.log",
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
