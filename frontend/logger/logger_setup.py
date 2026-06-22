# frontend\logger\logger_setup.py
import logging
import os
from dotenv import load_dotenv

from logging.handlers import RotatingFileHandler
from pathlib import Path

load_dotenv()
env = os.getenv("ENV")
DEV_LOG_PATH = r"C:\Users\hasan\Asija\mis"


def setup_logger():
    BASE_DIR = Path(__file__).resolve().parent.parent
    if env == "dev":
        BASE_DIR = Path(DEV_LOG_PATH)
    LOG_DIR = BASE_DIR / "logs"

    LOG_DIR.mkdir(exist_ok=True)

    file_handler = RotatingFileHandler(
        LOG_DIR / "frontend.log",
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
