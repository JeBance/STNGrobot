"""
Обработчики команд специалиста.
"""
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from db.models import UserRole, AssignmentStatus
from utils.repositories import UserRepository, SpecialistRepository, AssignmentRepository

logger = logging.getLogger("bot")
router = Router()


@router.message(Command("my_requests"))
async def cmd_spec_my_requests(message: Message, session):
    """Показать заявки специалиста."""
    user_repo = UserRepository(session)
    spec_repo = SpecialistRepository(session)
    assignment_repo = AssignmentRepository(session)
    
    user = await user_repo.get_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start")
        return

    specialist = await spec_repo.get_by_user_id(user.id)
    if not specialist:
        await message.answer("❌ Вы не являетесь специалистом.")
        return

    assignments = await assignment_repo.get_pending_by_specialist(specialist.id)

    if not assignments:
        await message.answer("📋 У вас нет активных заявок.")
        return

    text = "📋 Ваши активные заявки:\n\n"
    for assignment in assignments[:20]:
        request = assignment.request
        req_user = request.user
        text += f"#{request.id} от {req_user.full_name}: {request.text[:50]}...\n"

    if len(assignments) > 20:
        text += f"\n... и ещё {len(assignments) - 20} заявок"

    await message.answer(text)
