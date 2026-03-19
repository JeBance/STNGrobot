"""
Главный файл запуска Telegram-бота STNGrobot.
"""
import asyncio
import html
import logging
import logging.config
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message

from db import Database
from db.models import UserRole
from utils.config import BOT_TOKEN, ROOT_ID, DATABASE_URL, LOG_LEVEL, get_logger, notify_admin
from utils.rate_limiter import request_limiter
from bot.middleware import DatabaseMiddleware
from bot.handlers import (
    start_router,
    admin_router,
    user_router,
    specialist_router,
    callback_router,
)
from bot.keyboards import get_groups_keyboard

# Настройка логирования
log_config_path = Path(__file__).parent.parent / "logging.ini"
if log_config_path.exists():
    logging.config.fileConfig(log_config_path, disable_existing_loggers=False)
else:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

logger = get_logger("bot.main")
logger.setLevel(logging.DEBUG)

# Создаём базу данных
db = Database(DATABASE_URL)

# Создаём диспетчер
dp = Dispatcher()

# Создаём бота (глобальная переменная, как в youtube-downloader-bot)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# Регистрируем middleware для сессии БД
dp.update.middleware(DatabaseMiddleware(session_getter=db.get_session))

# Глобальный обработчик ошибок
@dp.errors()
async def errors_handler(update, exception):
    """Обработчик глобальных ошибок."""
    import traceback
    error_text = f"Ошибка в update {update.update_id}:\n{type(exception).__name__}: {str(exception)[:500]}\n\n{traceback.format_exc()[:1000]}"
    logger.error(error_text)
    
    # Уведомляем админа об ошибке
    await notify_admin(bot, error_text[:3000])
    
    return True

# Обработчик текстовых сообщений - создание заявки
# Регистрируем ПЕРЕД роутерами, но с фильтром для игнорирования команд
@dp.message(lambda m: m.text and not m.text.startswith("/"))
async def handle_text_message(message: Message, session):
    """Обработка текстовых сообщений - создание заявки."""
    logger.debug(f"Получено сообщение от {message.from_user.id}: {message.text}")

    # Проверка rate limiting
    user_id = message.from_user.id
    if not request_limiter.is_allowed(user_id):
        remaining_time = request_limiter.get_remaining_time(user_id)
        await message.answer(
            f"⚠️ Слишком много заявок! Пожалуйста, подождите {remaining_time} сек.\n"
            f"Максимум 5 заявок в минуту.",
            parse_mode=None
        )
        logger.warning(f"Rate limit превышен для пользователя {user_id}")
        return

    from utils.repositories import UserRepository, RequestRepository, GroupRepository
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    user_repo = UserRepository(session)
    request_repo = RequestRepository(session)
    group_repo = GroupRepository(session)

    # Получаем или создаём пользователя
    user = await user_repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    # Создаём заявку
    request = await request_repo.create(user_id=user.id, text=message.text)

    # Ответ пользователю
    await message.answer(
        f"✅ Заявка #{request.id} принята.\n"
        f"Ожидайте назначения специалиста."
    )

    # Уведомляем админов
    admins = await user_repo.get_all_by_role(UserRole.ADMIN)
    roots = await user_repo.get_all_by_role(UserRole.ROOT)
    all_admins = admins + roots

    groups = await group_repo.get_all()

    text = (
        f"🆕 Новая заявка #{request.id}\n\n"
        f"От: {html.escape(user.full_name)}\n"
        f"Username: @{html.escape(user.username or 'нет')}\n"
        f"ID: {user.telegram_id}\n\n"
        f"Текст: {html.escape(request.text)}"
    )

    if groups:
        keyboard = get_groups_keyboard(groups, request.id)
    else:
        builder = InlineKeyboardBuilder()
        builder.button(text="⚠️ Нет доступных групп", callback_data="no_groups")
        builder.button(text="❌ Отклонить", callback_data=f"request_cancel:{request.id}")
        builder.adjust(1)
        keyboard = builder.as_markup()

    for admin_user in all_admins:
        try:
            await bot.send_message(admin_user.telegram_id, text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Не удалось уведомить адина {admin_user.telegram_id}: {e}")

    logger.info(f"Создана заявка #{request.id} от пользователя {user.telegram_id}")


# Регистрируем роутеры ПОСЛЕ общего обработчика
dp.include_router(start_router)
dp.include_router(admin_router)
dp.include_router(user_router)
dp.include_router(specialist_router)
dp.include_router(callback_router)


# Хук при запуске
@dp.startup()
async def on_startup(bot: Bot):
    """Действия при запуске бота."""
    logger.info("=== ЗАПУСК БОТА ===")
    await db.create_tables()
    logger.info("База данных готова")
    
    # Проверяем root ID
    if ROOT_ID:
        try:
            root_user = await bot.get_chat(ROOT_ID)
            logger.info(f"Root админ: {root_user.full_name} (@{root_user.username})")
        except Exception as e:
            logger.warning(f"Не удалось получить информацию о root: {e}")
    
    # Устанавливаем команды бота
    from aiogram.types import BotCommand
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="admin", description="Панель администратора"),
        BotCommand(command="my_requests", description="Мои заявки"),
        BotCommand(command="help", description="Справка"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Команды бота установлены")


# Хук при остановке
@dp.shutdown()
async def on_shutdown(bot: Bot):
    """Действия при остановке бота."""
    await db.dispose()
    await bot.session.close()
    logger.info("Бот остановлен")


async def main():
    """Точка входа."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не указан в переменных окружения!")
        return

    try:
        logger.info("Запуск polling...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Остановка бота по Ctrl+C")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
