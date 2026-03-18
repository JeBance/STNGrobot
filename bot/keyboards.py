"""
Inline-клавиатуры для бота.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.models import Group, Specialist, Request, RequestStatus, UserRole


def get_groups_keyboard(groups: list[Group], request_id: int) -> InlineKeyboardMarkup:
    """Клавиатура с группами специалистов для админа."""
    builder = InlineKeyboardBuilder()

    for group in groups:
        builder.button(
            text=f"{group.name}",
            callback_data=f"group_select:{group.id}:{request_id}",
        )

    builder.button(text="❌ Отклонить", callback_data=f"request_cancel:{request_id}")
    builder.adjust(1)

    return builder.as_markup()


def get_specialists_keyboard(
    specialists: list[Specialist], group_id: int, request_id: int
) -> InlineKeyboardMarkup:
    """Клавиатура со специалистами группы."""
    builder = InlineKeyboardBuilder()

    for spec in specialists:
        user = spec.user
        builder.button(
            text=f"👤 {user.full_name}",
            callback_data=f"spec_select:{spec.id}:{request_id}",
        )

    # Кнопка "Отправить всем"
    builder.button(
        text="📢 Отправить всем",
        callback_data=f"send_to_all:{group_id}:{request_id}",
    )

    builder.button(text="⬅️ Назад", callback_data=f"back_to_groups:{request_id}")
    builder.adjust(1)

    return builder.as_markup()


def get_request_status_keyboard(request_id: int) -> InlineKeyboardMarkup:
    """Клавиатура статуса заявки для специалиста."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="✅ Выполнено",
        callback_data=f"request_complete:{request_id}",
    )

    return builder.as_markup()


def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура админ-меню."""
    builder = InlineKeyboardBuilder()

    builder.button(text="📋 Новые заявки", callback_data="admin_new_requests")
    builder.button(text="📊 Все заявки", callback_data="admin_all_requests")
    builder.button(text="👥 Специалисты", callback_data="admin_specialists")
    builder.button(text="📁 Группы", callback_data="admin_groups")
    builder.adjust(2)

    return builder.as_markup()


def get_spec_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура меню специалиста."""
    builder = InlineKeyboardBuilder()

    builder.button(text="📋 Мои заявки", callback_data="spec_my_requests")
    builder.adjust(1)

    return builder.as_markup()


def get_user_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура меню пользователя."""
    builder = InlineKeyboardBuilder()

    builder.button(text="📝 Создать заявку", callback_data="user_new_request")
    builder.button(text="📋 Мои заявки", callback_data="user_my_requests")
    builder.adjust(1)

    return builder.as_markup()


def get_request_info_keyboard(request_id: int, can_assign: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для просмотра информации о заявке."""
    builder = InlineKeyboardBuilder()

    if can_assign:
        builder.button(text="📋 Назначить", callback_data=f"assign_request:{request_id}")

    builder.button(text="🔙 Назад", callback_data="back_to_requests")
    builder.adjust(1)

    return builder.as_markup()


def get_yes_no_keyboard(callback_prefix: str, value: str) -> InlineKeyboardMarkup:
    """Клавиатура Да/Нет."""
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Да", callback_data=f"{callback_prefix}_yes:{value}")
    builder.button(text="❌ Нет", callback_data=f"{callback_prefix}_no:{value}")
    builder.adjust(2)

    return builder.as_markup()


def get_pagination_keyboard(
    page: int, total_pages: int, callback_prefix: str, **kwargs
) -> InlineKeyboardMarkup:
    """Клавиатура пагинации."""
    builder = InlineKeyboardBuilder()

    if page > 0:
        builder.button(
            text="⬅️ Назад",
            callback_data=f"{callback_prefix}_page:{page - 1}",
        )

    if page < total_pages - 1:
        builder.button(
            text="Вперёд ➡️",
            callback_data=f"{callback_prefix}_page:{page + 1}",
        )

    builder.adjust(2)
    return builder.as_markup()
