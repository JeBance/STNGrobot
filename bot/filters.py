"""
Фильтры для проверки прав доступа.
"""
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import UserRole
from utils.repositories import UserRepository
from utils.config import ROOT_ID


class RoleFilter(BaseFilter):
    """Фильтр для проверки роли пользователя."""

    allowed_roles: list[UserRole]

    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self, event: Message | CallbackQuery, session: AsyncSession
    ) -> bool:
        user_id = event.from_user.id
        repo = UserRepository(session)
        user = await repo.get_by_telegram_id(user_id)

        if not user:
            # Создаём пользователя если не найден
            user = await repo.get_or_create(
                telegram_id=user_id,
                username=event.from_user.username,
                first_name=event.from_user.first_name,
                last_name=event.from_user.last_name,
            )

        # Root всегда имеет доступ
        if user.role == UserRole.ROOT:
            return True

        return user.role in self.allowed_roles


class RootFilter(RoleFilter):
    """Фильтр только для root."""

    def __init__(self):
        super().__init__([UserRole.ROOT])


class AdminFilter(RoleFilter):
    """Фильтр для admin и root."""

    def __init__(self):
        super().__init__([UserRole.ADMIN, UserRole.ROOT])


class SpecFilter(RoleFilter):
    """Фильтр для spec, admin и root."""

    def __init__(self):
        super().__init__([UserRole.SPEC, UserRole.ADMIN, UserRole.ROOT])


class IsRootUser(BaseFilter):
    """Проверка что пользователь - root по ID."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return event.from_user.id == ROOT_ID
