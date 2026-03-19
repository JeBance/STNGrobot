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


async def notify_admin(bot, message: str):
    """
    Отправить уведомление супер-админу об ошибке.
    
    :param bot: Экземпляр бота
    :param message: Сообщение об ошибке
    """
    if ROOT_ID:
        try:
            await bot.send_message(
                ROOT_ID,
                f"⚠️ Ошибка в работе бота:\n\n{message}",
                parse_mode=None
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу: {e}")
