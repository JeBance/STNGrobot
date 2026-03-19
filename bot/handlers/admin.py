"""
Обработчики команд администратора.
"""
import html
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from db.models import UserRole, RequestStatus
from utils.repositories import UserRepository, GroupRepository, SpecialistRepository, RequestRepository
from utils.config import ROOT_ID

logger = logging.getLogger("bot")
router = Router()


@router.message(Command("admin"))
async def cmd_admin(message: Message, session):
    """Панель администратора."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user or user.role not in [UserRole.ADMIN, UserRole.ROOT]:
        await message.answer("❌ У вас нет прав для использования этой команды.")
        return

    text = (
        "🛠 Панель администратора\n\n"
        "Управление заявками:\n"
        "/requests [status] - список заявок (new/assigned/completed/cancelled)\n\n"
        "Управление группами:\n"
        "/add_group <название> - создать группу\n"
        "/delete_group <название> - удалить группу\n"
        "/list_groups - список групп\n\n"
        "Управление специалистами:\n"
        "/add_spec <telegram_id> <группа> - добавить специалиста\n"
        "/remove_spec <telegram_id> - удалить специалиста\n"
        "/list_specs - список специалистов\n\n"
        "Только для root:\n"
        "/add_admin <telegram_id> - назначить админа\n"
        "/remove_admin <telegram_id> - снять админа\n"
        "/list_admins - список админов\n"
        "/users - все пользователи"
    )
    await message.answer(text, parse_mode=None)


@router.message(Command("add_admin"))
async def cmd_add_admin(message: Message, session):
    """Назначить админа (только root)."""
    user_repo = UserRepository(session)

    if message.from_user.id != ROOT_ID:
        await message.answer("❌ Только супер-админ может назначать админов.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Использование: /add_admin <telegram_id>")
        return

    try:
        target_id = int(args[1])
    except ValueError:
        await message.answer("❌ Telegram ID должен быть числом.")
        return

    user = await user_repo.get_by_telegram_id(target_id)
    if not user:
        await message.answer(f"❌ Пользователь с ID {target_id} не найден.")
        return

    if user.role in [UserRole.ADMIN, UserRole.ROOT]:
        await message.answer(f"❌ Пользователь {html.escape(user.full_name)} уже является админом.")
        return

    await user_repo.update_role(user, UserRole.ADMIN)
    await message.answer(f"✅ Пользователь {html.escape(user.full_name)} назначен админом.")

    # Уведомляем нового админа
    try:
        await message.bot.send_message(
            target_id,
            "🎉 Вы назначены администратором системы STNGrobot!\n\n"
            "Теперь вы можете управлять заявками и специалистами.\n"
            "Используйте команду /admin для просмотра доступных команд.",
            parse_mode=None
        )
    except Exception as e:
        logger.warning(f"Не удалось отправить уведомление пользователю {target_id}: {e}")

    logger.info(f"Root {message.from_user.id} назначил админа {target_id}")


@router.message(Command("remove_admin"))
async def cmd_remove_admin(message: Message, session):
    """Снять админа (только root)."""
    user_repo = UserRepository(session)

    if message.from_user.id != ROOT_ID:
        await message.answer("❌ Только супер-админ может снимать админов.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Использование: /remove_admin <telegram_id>")
        return

    try:
        target_id = int(args[1])
    except ValueError:
        await message.answer("❌ Telegram ID должен быть числом.")
        return

    user = await user_repo.get_by_telegram_id(target_id)
    if not user:
        await message.answer(f"❌ Пользователь с ID {target_id} не найден.")
        return

    if user.role != UserRole.ADMIN:
        await message.answer(f"❌ Пользователь {html.escape(user.full_name)} не является админом.")
        return

    await user_repo.update_role(user, UserRole.USER)
    await message.answer(f"✅ Пользователь {html.escape(user.full_name)} снят с должности админа.")

    # Уведомляем
    try:
        await message.bot.send_message(
            target_id,
            "ℹ️ Вы больше не являетесь администратором системы STNGrobot.",
            parse_mode=None
        )
    except Exception as e:
        logger.warning(f"Не удалось отправить уведомление пользователю {target_id}: {e}")

    logger.info(f"Root {message.from_user.id} снял админа {target_id}")


@router.message(Command("list_admins"))
async def cmd_list_admins(message: Message, session):
    """Список админов."""
    user_repo = UserRepository(session)
    admins = await user_repo.get_all_by_role(UserRole.ADMIN)

    if not admins:
        await message.answer("📋 Список админов пуст.")
        return

    text = "📋 Список админов:\n\n"
    for admin in admins:
        text += f"• {html.escape(admin.full_name)} (@{admin.username or 'нет'}) - ID: {admin.telegram_id}\n"

    await message.answer(text, parse_mode=None)


@router.message(Command("users"))
async def cmd_users(message: Message, session):
    """Список всех пользователей (только root)."""
    user_repo = UserRepository(session)

    if message.from_user.id != ROOT_ID:
        await message.answer("❌ Только супер-админ может просматривать всех пользователей.")
        return

    users = await user_repo.get_all_users()

    if not users:
        await message.answer("📋 Список пользователей пуст.")
        return

    text = "👥 Все пользователи:\n\n"
    for user in users:
        text += f"• {html.escape(user.full_name)} (@{user.username or 'нет'}) - ID: {user.telegram_id} - Роль: {user.role.value}\n"

    if len(text) > 4096:
        text = text[:4093] + "..."

    await message.answer(text, parse_mode=None)


@router.message(Command("add_group"))
async def cmd_add_group(message: Message, session):
    """Создать группу специалистов."""
    user_repo = UserRepository(session)
    group_repo = GroupRepository(session)

    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user or user.role not in [UserRole.ADMIN, UserRole.ROOT]:
        await message.answer("❌ У вас нет прав для создания групп.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Использование: /add_group <название группы>")
        return

    group_name = args[1].strip()

    existing = await group_repo.get_by_name(group_name)
    if existing:
        await message.answer(f"❌ Группа '{html.escape(group_name)}' уже существует.")
        return

    await group_repo.create(name=group_name, created_by=user.id)
    await message.answer(f"✅ Группа '{html.escape(group_name)}' создана.", parse_mode=None)

    logger.info(f"Admin {user.telegram_id} создал группу '{group_name}'")


@router.message(Command("delete_group"))
async def cmd_delete_group(message: Message, session):
    """Удалить группу специалистов."""
    user_repo = UserRepository(session)
    group_repo = GroupRepository(session)
    spec_repo = SpecialistRepository(session)

    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user or user.role not in [UserRole.ADMIN, UserRole.ROOT]:
        await message.answer("❌ У вас нет прав для удаления групп.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Использование: /delete_group <название группы>")
        return

    group_name = args[1].strip()
    group = await group_repo.get_by_name(group_name)

    if not group:
        await message.answer(f"❌ Группа '{html.escape(group_name)}' не найдена.")
        return

    # Проверяем есть ли специалисты в группе
    specialists = await spec_repo.get_by_group(group.id)
    if specialists:
        await message.answer(
            f"❌ Нельзя удалить группу '{html.escape(group_name)}', в ней есть специалисты ({len(specialists)}).\n"
            f"Сначала удалите специалистов из группы.",
            parse_mode=None
        )
        return

    await group_repo.delete(group)
    await message.answer(f"✅ Группа '{html.escape(group_name)}' удалена.", parse_mode=None)

    logger.info(f"Admin {user.telegram_id} удалил группу '{group_name}'")


@router.message(Command("list_groups"))
async def cmd_list_groups(message: Message, session):
    """Список групп."""
    user_repo = UserRepository(session)
    group_repo = GroupRepository(session)

    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user or user.role not in [UserRole.ADMIN, UserRole.ROOT, UserRole.SPEC]:
        await message.answer("❌ У вас нет прав для просмотра групп.")
        return

    groups_with_count = await group_repo.get_with_specialists_count()

    if not groups_with_count:
        await message.answer("📋 Список групп пуст.")
        return

    text = "📁 Группы специалистов:\n\n"
    for group, count in groups_with_count:
        text += f"• {html.escape(group.name)} - {count} специалистов\n"

    await message.answer(text, parse_mode=None)


@router.message(Command("add_spec"))
async def cmd_add_spec(message: Message, session):
    """Добавить специалиста в группу."""
    user_repo = UserRepository(session)
    group_repo = GroupRepository(session)
    spec_repo = SpecialistRepository(session)

    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user or user.role not in [UserRole.ADMIN, UserRole.ROOT]:
        await message.answer("❌ У вас нет прав для добавления специалистов.")
        return

    args = message.text.split()
    if len(args) < 3:
        await message.answer("❌ Использование: /add_spec <telegram_id> <группа>")
        return

    try:
        target_id = int(args[1])
    except ValueError:
        await message.answer("❌ Telegram ID должен быть числом.")
        return

    group_name = args[2]
    group = await group_repo.get_by_name(group_name)

    if not group:
        await message.answer(f"❌ Группа '{html.escape(group_name)}' не найдена.")
        return

    target_user = await user_repo.get_by_telegram_id(target_id)
    if not target_user:
        await message.answer(f"❌ Пользователь с ID {target_id} не найден.")
        return

    # Проверяем не является ли уже специалистом
    existing_spec = await spec_repo.get_by_user_id(target_user.id)
    if existing_spec:
        await message.answer(f"❌ Пользователь {html.escape(target_user.full_name)} уже является специалистом.")
        return

    # Создаём специалиста
    await spec_repo.create(user_id=target_user.id, group_id=group.id, assigned_by=user.id)

    # Меняем роль пользователя
    await user_repo.update_role(target_user, UserRole.SPEC)

    await message.answer(
        f"✅ Пользователь {html.escape(target_user.full_name)} добавлен в группу '{html.escape(group.name)}'.",
        parse_mode=None
    )

    # Уведомляем специалиста
    try:
        await message.bot.send_message(
            target_id,
            f"🎉 Вы назначены специалистом в группе '{html.escape(group.name)}'!\n\n"
            f"Теперь вы будете получать заявки для выполнения.",
            parse_mode=None
        )
    except Exception as e:
        logger.warning(f"Не удалось отправить уведомление пользователю {target_id}: {e}")

    logger.info(f"Admin {user.telegram_id} добавил специалиста {target_id} в группу '{group_name}'")


@router.message(Command("remove_spec"))
async def cmd_remove_spec(message: Message, session):
    """Удалить специалиста."""
    user_repo = UserRepository(session)
    spec_repo = SpecialistRepository(session)

    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user or user.role not in [UserRole.ADMIN, UserRole.ROOT]:
        await message.answer("❌ У вас нет прав для удаления специалистов.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Использование: /remove_spec <telegram_id>")
        return

    try:
        target_id = int(args[1])
    except ValueError:
        await message.answer("❌ Telegram ID должен быть числом.")
        return

    target_user = await user_repo.get_by_telegram_id(target_id)
    if not target_user:
        await message.answer(f"❌ Пользователь с ID {target_id} не найден.")
        return

    specialist = await spec_repo.get_by_user_id(target_user.id)
    if not specialist:
        await message.answer(f"❌ Пользователь {html.escape(target_user.full_name)} не является специалистом.")
        return

    # Удаляем специалиста
    await spec_repo.delete(specialist)

    # Меняем роль обратно на user
    await user_repo.update_role(target_user, UserRole.USER)

    await message.answer(f"✅ Пользователь {html.escape(target_user.full_name)} удалён из специалистов.", parse_mode=None)

    # Уведомляем
    try:
        await message.bot.send_message(
            target_id,
            "ℹ️ Вы больше не являетесь специалистом системы STNGrobot.",
            parse_mode=None
        )
    except Exception as e:
        logger.warning(f"Не удалось отправить уведомление пользователю {target_id}: {e}")

    logger.info(f"Admin {user.telegram_id} удалил специалиста {target_id}")


@router.message(Command("list_specs"))
async def cmd_list_specs(message: Message, session):
    """Список всех специалистов."""
    user_repo = UserRepository(session)
    spec_repo = SpecialistRepository(session)

    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user or user.role not in [UserRole.ADMIN, UserRole.ROOT]:
        await message.answer("❌ У вас нет прав для просмотра списка специалистов.")
        return

    specialists = await spec_repo.get_all_with_groups()

    if not specialists:
        await message.answer("📋 Список специалистов пуст.")
        return

    text = "👥 Специалисты:\n\n"
    for spec in specialists:
        user_obj = spec.user
        group = spec.group
        text += f"• {html.escape(user_obj.full_name)} (@{user_obj.username or 'нет'}) - Группа: {html.escape(group.name)}\n"

    await message.answer(text, parse_mode=None)


@router.message(Command("requests"))
async def cmd_requests(message: Message, session):
    """Список заявок с фильтрацией по статусу."""
    user_repo = UserRepository(session)
    request_repo = RequestRepository(session)

    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user or user.role not in [UserRole.ADMIN, UserRole.ROOT]:
        await message.answer("❌ У вас нет прав для просмотра заявок.")
        return

    args = message.text.split()
    status_filter = args[1].lower() if len(args) > 1 else None

    status_map = {
        "new": RequestStatus.NEW,
        "assigned": RequestStatus.ASSIGNED,
        "completed": RequestStatus.COMPLETED,
        "cancelled": RequestStatus.CANCELLED,
    }

    if status_filter and status_filter not in status_map:
        await message.answer(
            "❌ Неверный статус. Доступные: new, assigned, completed, cancelled",
            parse_mode=None
        )
        return

    if status_filter:
        requests = await request_repo.get_by_status(status_map[status_filter])
    else:
        requests = await request_repo.get_all()

    if not requests:
        await message.answer(f"📋 Заявок {'с таким статусом ' if status_filter else ''}не найдено.", parse_mode=None)
        return

    text = f"📋 Заявки{' (' + status_filter + ')' if status_filter else ''}:\n\n"
    for req in requests[:20]:  # Ограничим 20 заявками
        user_obj = req.user
        status_emoji = {"new": "🆕", "assigned": "📝", "completed": "✅", "cancelled": "❌"}
        text += f"#{req.id} {status_emoji.get(req.status.value, '•')} {html.escape(user_obj.full_name)}: {html.escape(req.text[:50])}...\n"

    if len(requests) > 20:
        text += f"\n... и ещё {len(requests) - 20} заявок"

    await message.answer(text, parse_mode=None)
