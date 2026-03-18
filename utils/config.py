"""
Конфигурация и настройки бота.
"""
import os
import logging
import logging.config
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройки бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ROOT_ID = int(os.getenv("ROOT_ID", "0"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/stngrobot_db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Настройка логирования
log_config_path = Path(__file__).parent.parent / "logging.ini"
if log_config_path.exists():
    logging.config.fileConfig(log_config_path)

logger = logging.getLogger("bot")


def get_logger(name: str = "bot") -> logging.Logger:
    """Получить логгер по имени."""
    return logging.getLogger(name)
