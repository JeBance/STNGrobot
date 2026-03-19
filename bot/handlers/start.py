"""
Обработчик команды /start и регистрация пользователей.
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

from db.models import UserRole
from utils.repositories import UserRepository

logger = logging.getLogger("bot")
router = Router()


def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отправки номера телефона."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


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
                "/add_spec - добавить специалиста",
                parse_mode=None
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
                "/list_groups - список групп",
                parse_mode=None
            )
        elif user.role == UserRole.SPEC:
            await message.answer(
                f"👋 Привет, {user.full_name}!\n\n"
                "Вы - специалист системы.\n\n"
                "Доступные команды:\n"
                "/my_requests - мои заявки\n"
                "Просто отправьте текст боту для создания заявки",
                parse_mode=None
            )
        else:
            await message.answer(
                f"👋 Привет, {user.full_name}!\n\n"
                "Вы зарегистрированы в системе.\n\n"
                "Просто отправьте текст боту для создания заявки.\n"
                "/my_requests - история ваших заявок",
                parse_mode=None
            )
    else:
        # Создаём нового пользователя с ролью USER
        user = await user_repo.get_or_create(
            telegram_id=telegram_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            role=UserRole.USER,
        )

        # Предлагаем отправить номер телефона
        await message.answer(
            f"👋 Привет, {user.full_name}!\n\n"
            "Вы зарегистрированы в системе диспетчерской службы.\n\n"
            "Для быстрой связи с вами рекомендуем отправить номер телефона.\n"
            "Вы можете сделать это сейчас или пропустить этот шаг.\n\n"
            "Команды:\n"
            "/my_requests - история ваших заявок\n"
            "/start - показать это сообщение\n\n"
            "Просто отправьте текст боту для создания заявки.",
            reply_markup=get_phone_keyboard(),
            parse_mode=None
        )

    logger.info(f"Пользователь {telegram_id} ({user.full_name}) использовал /start")


@router.message(F.contact)
async def handle_phone_contact(message: Message, session):
    """Обработка отправленного контакта (номера телефона)."""
    user_repo = UserRepository(session)
    
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if user:
        # Сохраняем номер телефона
        from sqlalchemy import update
        await session.execute(
            update(type(user))
            .where(type(user).id == user.id)
            .values(phone=message.contact.phone_number)
        )
        await session.commit()
        
        await message.answer(
            f"✅ Спасибо! Номер телефона {message.contact.phone_number} сохранён.\n\n"
            "Теперь вы можете создать заявку, просто отправив текстовое сообщение.",
            reply_markup=None,  # Убираем клавиатуру
            parse_mode=None
        )
        logger.info(f"Пользователь {user.telegram_id} отправил номер телефона: {message.contact.phone_number}")
    else:
        # Если пользователь не найден, убираем клавиатуру
        await message.answer(
            "❌ Произошла ошибка. Пожалуйста, нажмите /start для регистрации.",
            reply_markup=None,
            parse_mode=None
        )
