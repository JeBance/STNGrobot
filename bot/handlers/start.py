"""
Обработчик команды /start и регистрация пользователей.
"""
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from db.models import UserRole
from utils.repositories import UserRepository

logger = logging.getLogger("bot")
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, session):
    """Обработка команды /start."""
    telegram_id = message.from_user.id
    user_repo = UserRepository(session)

    # Проверяем существующего пользователя
    user = await user_repo.get_by_telegram_id(telegram_id)

    if user:
        if user.role == UserRole.ROOT:
            await message.answer(
                f"👋 Привет, {user.full_name}!\n\n"
                "Вы - супер-админ системы.\n\n"
                "Доступные команды:\n"
                "/admin - панель администратора\n"
                "/add_admin <ID> - назначить админа\n"
                "/remove_admin <ID> - снять админа\n"
                "/list_admins - список админов\n"
                "/users - все пользователи\n"
                "/requests - список заявок\n"
                "/add_group - создать группу\n"
                "/add_spec - добавить специалиста"
            )
        elif user.role == UserRole.ADMIN:
            await message.answer(
                f"👋 Привет, {user.full_name}!\n\n"
                "Вы - администратор системы.\n\n"
                "Доступные команды:\n"
                "/admin - панель администратора\n"
                "/requests - список заявок\n"
                "/add_group - создать группу\n"
                "/delete_group - удалить группу\n"
                "/add_spec - добавить специалиста\n"
                "/remove_spec - удалить специалиста\n"
                "/list_specs - список специалистов\n"
                "/list_groups - список групп"
            )
        elif user.role == UserRole.SPEC:
            await message.answer(
                f"👋 Привет, {user.full_name}!\n\n"
                "Вы - специалист системы.\n\n"
                "Доступные команды:\n"
                "/my_requests - мои заявки\n"
                "Просто отправьте текст боту для создания заявки"
            )
        else:
            await message.answer(
                f"👋 Привет, {user.full_name}!\n\n"
                "Вы зарегистрированы в системе.\n\n"
                "Просто отправьте текст боту для создания заявки.\n"
                "/my_requests - история ваших заявок"
            )
    else:
        # Создаём нового пользователя
        user = await user_repo.get_or_create(
            telegram_id=telegram_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            role=UserRole.USER,
        )

        await message.answer(
            f"👋 Привет, {user.full_name}!\n\n"
            "Вы зарегистрированы в системе диспетчерской службы.\n\n"
            "Просто отправьте текст боту для создания заявки.\n\n"
            "Команды:\n"
            "/my_requests - история ваших заявок\n"
            "/start - показать это сообщение"
        )

    logger.info(f"Пользователь {telegram_id} ({user.full_name}) использовал /start")
