"""
Главный файл запуска Telegram-бота STNGrobot.
"""
import asyncio
import logging
import logging.config
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message

from db import Database
from db.models import UserRole
from utils.config import BOT_TOKEN, ROOT_ID, DATABASE_URL, LOG_LEVEL, get_logger
from bot.middleware import DatabaseMiddleware
from bot.handlers import (
    start_router,
    admin_router,
    user_router,
    specialist_router,
    callback_router,
)

# Настройка логирования
log_config_path = Path(__file__).parent.parent / "logging.ini"
if log_config_path.exists():
    logging.config.fileConfig(log_config_path)

logger = get_logger("bot.main")


def create_app() -> Dispatcher:
    """Создание и настройка приложения."""
    # Создаём диспетчер
    dp = Dispatcher()

    # Создаём бота
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Создаём базу данных
    db = Database(DATABASE_URL)

    # Регистрируем middleware для сессии БД
    dp.update.middleware(DatabaseMiddleware(session_getter=db.get_session))

    # Регистрируем роутеры
    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(specialist_router)
    dp.include_router(callback_router)

    # Обработчик текстовых сообщений - создание заявки
    @dp.message()
    async def handle_text_message(message: Message, session):
        """Обработка текстовых сообщений - создание заявки."""
        if not message.text:
            return

        # Игнорируем команды
        if message.text.startswith("/"):
            return

        from utils.repositories import UserRepository, RequestRepository
        from utils.keyboards import get_groups_keyboard
        from db.models import UserRole
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
            f"От: {user.full_name}\n"
            f"Username: @{user.username or 'нет'}\n"
            f"ID: {user.telegram_id}\n\n"
            f"Текст: {request.text}"
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
                await bot.send_message(admin_user.telegram_id, text, reply_markup=keyboard)
            except Exception as e:
                logger.warning(f"Не удалось уведомить адина {admin_user.telegram_id}: {e}")

        logger.info(f"Создана заявка #{request.id} от пользователя {user.telegram_id}")

    # Хук при запуске
    @dp.startup()
    async def on_startup(bot: Bot):
        """Действия при запуске бота."""
        await db.create_tables()
        logger.info("Бот запущен")

        # Проверяем root ID
        if ROOT_ID:
            try:
                root_user = await bot.get_chat(ROOT_ID)
                logger.info(f"Root админ: {root_user.full_name}")
            except Exception as e:
                logger.warning(f"Не удалось получить информацию о root: {e}")

    # Хук при остановке
    @dp.shutdown()
    async def on_shutdown(bot: Bot):
        """Действия при остановке бота."""
        await db.dispose()
        await bot.session.close()
        logger.info("Бот остановлен")

    return dp


async def main():
    """Точка входа."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не указан в переменных окружения!")
        return

    dp = create_app()

    try:
        await dp.start_polling()
    except KeyboardInterrupt:
        logger.info("Остановка бота по Ctrl+C")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
