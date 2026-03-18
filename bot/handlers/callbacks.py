"""
Обработчики callback-запросов (inline-кнопок).
"""
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select

from db.models import UserRole, RequestStatus, AssignmentStatus, Specialist, Group, RequestAssignment
from utils.repositories import (
    UserRepository,
    GroupRepository,
    SpecialistRepository,
    RequestRepository,
    AssignmentRepository,
)
from utils.keyboards import (
    get_groups_keyboard,
    get_specialists_keyboard,
    get_request_status_keyboard,
)

logger = logging.getLogger("bot")
router = Router()


@router.callback_query(F.data.startswith("group_select:"))
async def callback_group_select(
    callback: CallbackQuery,
    session,
):
    """Выбор группы специалистов админом."""
    user_repo = UserRepository(session)
    group_repo = GroupRepository(session)
    spec_repo = SpecialistRepository(session)
    request_repo = RequestRepository(session)
    
    admin = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not admin or admin.role not in [UserRole.ADMIN, UserRole.ROOT]:
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    # Парсим callback_data: group_select:{group_id}:{request_id}
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Ошибка данных", show_alert=True)
        return

    group_id = int(parts[1])
    request_id = int(parts[2])

    # Получаем заявку
    request = await request_repo.get_by_id(request_id)
    if not request:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    # Получаем группу по ID
    result = await session.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()

    if not group:
        await callback.answer("❌ Группа не найдена", show_alert=True)
        return

    # Получаем специалистов группы
    specialists = await spec_repo.get_by_group(group_id)

    if not specialists:
        await callback.answer("❌ В группе нет специалистов", show_alert=True)
        return

    # Формируем сообщение
    request_user = request.user
    text = (
        f"📋 Заявка #{request_id}\n"
        f"От: {request_user.full_name}\n"
        f"Текст: {request.text}\n\n"
        f"Группа: {group.name}\n"
        f"Выберите специалиста:"
    )

    keyboard = get_specialists_keyboard(specialists, group_id, request_id)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=keyboard)

    await callback.answer()


@router.callback_query(F.data.startswith("spec_select:"))
async def callback_spec_select(
    callback: CallbackQuery,
    session,
):
    """Выбор конкретного специалиста админом."""
    user_repo = UserRepository(session)
    request_repo = RequestRepository(session)
    spec_repo = SpecialistRepository(session)
    assignment_repo = AssignmentRepository(session)
    
    admin = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not admin or admin.role not in [UserRole.ADMIN, UserRole.ROOT]:
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    # Парсим: spec_select:{specialist_id}:{request_id}
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Ошибка данных", show_alert=True)
        return

    specialist_id = int(parts[1])
    request_id = int(parts[2])

    # Получаем сущности
    request = await request_repo.get_by_id(request_id)
    if not request:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    # Получаем специалиста по ID
    result = await session.execute(select(Specialist).where(Specialist.id == specialist_id))
    specialist = result.scalar_one_or_none()

    if not specialist:
        await callback.answer("❌ Специалист не найден", show_alert=True)
        return

    # Создаём назначение
    await assignment_repo.create(request_id=request_id, specialist_id=specialist_id)

    # Обновляем заявку
    await request_repo.update_status(
        request, RequestStatus.ASSIGNED, assigned_to=specialist_id
    )

    # Отправляем заявку специалисту
    request_user = request.user
    spec_user = specialist.user
    text = (
        f"🔔 Новая заявка #{request_id}\n\n"
        f"От: {request_user.full_name}\n"
        f"Текст: {request.text}\n\n"
        f"Нажмите 'Выполнено' после завершения работы."
    )

    keyboard = get_request_status_keyboard(request_id)

    try:
        await callback.bot.send_message(
            spec_user.telegram_id, text, reply_markup=keyboard
        )
    except TelegramBadRequest as e:
        logger.warning(f"Не удалось отправить заявку специалисту {spec_user.telegram_id}: {e}")
        await callback.answer("❌ Не удалось отправить заявку специалисту", show_alert=True)
        return

    await callback.message.edit_text(
        f"✅ Заявка #{request_id} назначена специалисту {spec_user.full_name}"
    )

    logger.info(f"Admin {admin.telegram_id} назначил заявку #{request_id} специалисту {spec_user.telegram_id}")
    await callback.answer()


@router.callback_query(F.data.startswith("send_to_all:"))
async def callback_send_to_all(
    callback: CallbackQuery,
    session,
):
    """Отправить заявку всем специалистам группы."""
    user_repo = UserRepository(session)
    request_repo = RequestRepository(session)
    spec_repo = SpecialistRepository(session)
    assignment_repo = AssignmentRepository(session)
    
    admin = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not admin or admin.role not in [UserRole.ADMIN, UserRole.ROOT]:
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    # Парсим: send_to_all:{group_id}:{request_id}
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("❌ Ошибка данных", show_alert=True)
        return

    group_id = int(parts[1])
    request_id = int(parts[2])

    # Получаем сущности
    request = await request_repo.get_by_id(request_id)
    if not request:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    specialists = await spec_repo.get_by_group(group_id)
    if not specialists:
        await callback.answer("❌ В группе нет специалистов", show_alert=True)
        return

    # Создаём назначения для всех специалистов
    for specialist in specialists:
        await assignment_repo.create(
            request_id=request_id, specialist_id=specialist.id
        )

    # Обновляем заявку
    await request_repo.update_status(
        request, RequestStatus.ASSIGNED, assigned_group=group_id
    )

    # Отправляем заявку всем специалистам
    request_user = request.user
    text = (
        f"🔔 Новая заявка #{request_id}\n\n"
        f"От: {request_user.full_name}\n"
        f"Текст: {request.text}\n\n"
        f"Заявка отправлена всей группе. Кто первый выполнит - тому зачёт!\n"
        f"Нажмите 'Выполнено' после завершения работы."
    )

    keyboard = get_request_status_keyboard(request_id)
    sent_count = 0

    for specialist in specialists:
        spec_user = specialist.user
        try:
            await callback.bot.send_message(
                spec_user.telegram_id, text, reply_markup=keyboard
            )
            sent_count += 1
        except TelegramBadRequest as e:
            logger.warning(f"Не удалось отправить заявку специалисту {spec_user.telegram_id}: {e}")

    await callback.message.edit_text(
        f"✅ Заявка #{request_id} отправлена {sent_count} специалистам группы"
    )

    logger.info(f"Admin {admin.telegram_id} отправил заявку #{request_id} всей группе ({sent_count} чел.)")
    await callback.answer()


@router.callback_query(F.data.startswith("back_to_groups:"))
async def callback_back_to_groups(
    callback: CallbackQuery,
    session,
):
    """Вернуться к выбору групп."""
    user_repo = UserRepository(session)
    group_repo = GroupRepository(session)
    request_repo = RequestRepository(session)
    
    admin = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not admin or admin.role not in [UserRole.ADMIN, UserRole.ROOT]:
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    # Парсим: back_to_groups:{request_id}
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("❌ Ошибка данных", show_alert=True)
        return

    request_id = int(parts[1])

    request = await request_repo.get_by_id(request_id)
    if not request:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    # Получаем все группы
    groups = await group_repo.get_all()

    if not groups:
        await callback.answer("❌ Нет доступных групп", show_alert=True)
        return

    request_user = request.user
    text = (
        f"📋 Заявка #{request_id}\n"
        f"От: {request_user.full_name}\n"
        f"Текст: {request.text}\n\n"
        f"Выберите группу специалистов:"
    )

    keyboard = get_groups_keyboard(groups, request_id)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=keyboard)

    await callback.answer()


@router.callback_query(F.data.startswith("request_complete:"))
async def callback_request_complete(
    callback: CallbackQuery,
    session,
):
    """Заявка выполнена специалистом."""
    user_repo = UserRepository(session)
    spec_repo = SpecialistRepository(session)
    request_repo = RequestRepository(session)
    assignment_repo = AssignmentRepository(session)
    
    # Парсим: request_complete:{request_id}
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("❌ Ошибка данных", show_alert=True)
        return

    request_id = int(parts[1])

    # Получаем пользователя и специалиста
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    specialist = await spec_repo.get_by_user_id(user.id)

    if not specialist:
        await callback.answer("❌ Вы не являетесь специалистом", show_alert=True)
        return

    # Получаем заявку
    request = await request_repo.get_by_id(request_id)
    if not request:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    # Проверяем не выполнена ли уже заявка
    if request.status == RequestStatus.COMPLETED:
        await callback.answer("✅ Эта заявка уже выполнена другим специалистом", show_alert=True)
        return

    # Проверяем есть ли назначение у этого специалиста
    assignment = (await session.execute(
        select(RequestAssignment).where(
            RequestAssignment.request_id == request_id,
            RequestAssignment.specialist_id == specialist.id,
        )
    )).scalar_one_or_none()

    if not assignment:
        await callback.answer("❌ У вас нет назначения на эту заявку", show_alert=True)
        return

    # Обновляем назначение
    await assignment_repo.update_status(
        assignment, AssignmentStatus.COMPLETED, completed_at=datetime.utcnow()
    )

    # Отменяем остальные назначения
    await assignment_repo.cancel_other_assignments(request_id, specialist.id)

    # Обновляем заявку
    await request_repo.update_status(
        request,
        RequestStatus.COMPLETED,
        completed_by=specialist.id,
        completed_at=datetime.utcnow(),
    )

    # Уведомляем админов
    admins = await user_repo.get_all_by_role(UserRole.ADMIN)
    root_users = await user_repo.get_all_by_role(UserRole.ROOT)
    all_admins = admins + root_users

    notification_text = (
        f"✅ Заявка #{request_id} выполнена!\n"
        f"Специалист: {user.full_name}"
    )

    for admin_user in all_admins:
        try:
            await callback.bot.send_message(admin_user.telegram_id, notification_text)
        except Exception as e:
            logger.warning(f"Не удалось уведомить адина {admin_user.telegram_id}: {e}")

    # Уведомляем пользователя
    request_user = request.user
    try:
        await callback.bot.send_message(
            request_user.telegram_id,
            f"✅ Ваша заявка #{request_id} выполнена специалистом {user.full_name}!",
        )
    except Exception as e:
        logger.warning(f"Не удалось уведомить пользователя {request_user.telegram_id}: {e}")

    # Удаляем кнопки у сообщения специалиста
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass

    await callback.answer("✅ Заявка отмечена как выполненная!")
    logger.info(f"Specialist {user.telegram_id} выполнил заявку #{request_id}")


@router.callback_query(F.data.startswith("request_cancel:"))
async def callback_request_cancel(
    callback: CallbackQuery,
    session,
):
    """Отклонить заявку админом."""
    user_repo = UserRepository(session)
    request_repo = RequestRepository(session)
    
    admin = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not admin or admin.role not in [UserRole.ADMIN, UserRole.ROOT]:
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    # Парсим: request_cancel:{request_id}
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("❌ Ошибка данных", show_alert=True)
        return

    request_id = int(parts[1])

    request = await request_repo.get_by_id(request_id)
    if not request:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    # Обновляем статус
    await request_repo.update_status(request, RequestStatus.CANCELLED)

    # Уведомляем пользователя
    request_user = request.user
    try:
        await callback.bot.send_message(
            request_user.telegram_id,
            f"❌ Ваша заявка #{request_id} отклонена администратором.",
        )
    except Exception as e:
        logger.warning(f"Не удалось уведомить пользователя {request_user.telegram_id}: {e}")

    await callback.message.edit_text(f"❌ Заявка #{request_id} отклонена")

    logger.info(f"Admin {admin.telegram_id} отклонил заявку #{request_id}")
    await callback.answer()


@router.callback_query(F.data == "no_groups")
async def callback_no_groups(callback: CallbackQuery):
    """Обработчик нажатия на 'Нет доступных групп'."""
    await callback.answer("⚠️ Администратор должен создать группы специалистов", show_alert=True)
