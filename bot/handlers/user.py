"""
Обработчики команд пользователя - создание заявок.
"""
import html
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from db.models import UserRole, RequestStatus
from utils.repositories import UserRepository, RequestRepository

logger = logging.getLogger("bot")
router = Router()


@router.message(Command("my_requests"))
async def cmd_my_requests(message: Message, session):
    """Показать историю заявок пользователя."""
    user_repo = UserRepository(session)
    request_repo = RequestRepository(session)

    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start", parse_mode=None)
        return

    requests = await request_repo.get_user_requests(user.id)

    if not requests:
        await message.answer("📋 У вас пока нет заявок.", parse_mode=None)
        return

    text = "📋 Ваши заявки:\n\n"
    status_emoji = {
        "new": "🆕",
        "assigned": "📝",
        "completed": "✅",
        "cancelled": "❌"
    }

    for req in requests[:20]:  # Ограничим 20 заявками
        emoji = status_emoji.get(req.status.value, "•")
        specialist_info = ""
        if req.status == RequestStatus.COMPLETED and req.specialist_completed:
            specialist_info = f" (выполнил: {html.escape(req.specialist_completed.user.full_name)})"

        text += f"{emoji} #{req.id} - {html.escape(req.text[:50])}...{specialist_info}\n"

    if len(requests) > 20:
        text += f"\n... и ещё {len(requests) - 20} заявок"

    await message.answer(text, parse_mode=None)


@router.message(Command("new_request"))
async def cmd_new_request(message: Message):
    """Подсказка по созданию заявки."""
    await message.answer(
        "📝 Чтобы создать заявку, просто отправьте текстовое сообщение боту.\n\n"
        "Опишите проблему в свободной форме, например:\n"
        "• 'Вагон Л-12. Не работает свет в тамбуре'\n"
        "• 'Протечка трубы на кухне'\n"
        "• 'Нужно заменить розетку'",
        parse_mode=None
    )


@router.message(Command("help"))
async def cmd_help(message: Message, session):
    """Справка по командам."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start", parse_mode=None)
        return

    if user.role == UserRole.USER:
        await message.answer(
            "📖 Справка\n\n"
            "Создание заявки:\n"
            "Просто отправьте текстовое сообщение боту\n\n"
            "Команды:\n"
            "/start - главное меню\n"
            "/my_requests - история заявок\n"
            "/help - эта справка",
            parse_mode=None
        )
    elif user.role == UserRole.SPEC:
        await message.answer(
            "📖 Справка специалиста\n\n"
            "Вы получаете заявки от администратора.\n"
            "Для выполнения используйте кнопку 'Выполнено'.\n\n"
            "Команды:\n"
            "/start - главное меню\n"
            "/my_requests - мои заявки\n"
            "/help - эта справка",
            parse_mode=None
        )
    elif user.role in [UserRole.ADMIN, UserRole.ROOT]:
        await message.answer(
            "📖 Справка администратора\n\n"
            "Управление заявками:\n"
            "/requests - список заявок\n\n"
            "Управление группами:\n"
            "/add_group <название> - создать группу\n"
            "/delete_group <название> - удалить группу\n"
            "/list_groups - список групп\n\n"
            "Управление специалистами:\n"
            "/add_spec <ID> <группа> - добавить специалиста\n"
            "/remove_spec <ID> - удалить специалиста\n"
            "/list_specs - список специалистов\n\n"
            "Только для root:\n"
            "/add_admin <ID> - назначить админа\n"
            "/remove_admin <ID> - снять админа\n"
            "/list_admins - список админов\n"
            "/users - все пользователи",
            parse_mode=None
        )
