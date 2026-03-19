"""
База данных репозиторий для работы с пользователями и сущностями.
"""
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    User, Group, Specialist, Request, RequestAssignment,
    UserRole, RequestStatus, AssignmentStatus
)


class UserRepository:
    """Репозиторий для работы с пользователями."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя по Telegram ID."""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, telegram_id: int, **kwargs) -> User:
        """Получить или создать пользователя."""
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            user = User(telegram_id=telegram_id, **kwargs)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
        return user

    async def update_role(self, user: User, role: UserRole) -> None:
        """Обновить роль пользователя."""
        user.role = role
        await self.session.commit()

    async def get_all_by_role(self, role: UserRole) -> List[User]:
        """Получить всех пользователей с указанной ролью."""
        result = await self.session.execute(
            select(User).where(User.role == role)
        )
        return list(result.scalars().all())

    async def get_all_users(self) -> List[User]:
        """Получить всех пользователей."""
        result = await self.session.execute(select(User))
        return list(result.scalars().all())


class GroupRepository:
    """Репозиторий для работы с группами."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_name(self, name: str) -> Optional[Group]:
        """Получить группу по названию."""
        result = await self.session.execute(
            select(Group).where(Group.name == name)
        )
        return result.scalar_one_or_none()

    async def create(self, name: str, created_by: int) -> Group:
        """Создать новую группу."""
        group = Group(name=name, created_by=created_by)
        self.session.add(group)
        await self.session.commit()
        await self.session.refresh(group)
        return group

    async def delete(self, group: Group) -> None:
        """Удалить группу."""
        await self.session.delete(group)
        await self.session.commit()

    async def get_all(self) -> List[Group]:
        """Получить все группы."""
        result = await self.session.execute(select(Group))
        return list(result.scalars().all())

    async def get_with_specialists_count(self) -> List[tuple]:
        """Получить все группы с количеством специалистов."""
        result = await self.session.execute(
            select(Group, func.count(Specialist.id))
            .outerjoin(Specialist)
            .group_by(Group.id)
        )
        return result.all()


class SpecialistRepository:
    """Репозиторий для работы со специалистами."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_id(self, user_id: int) -> Optional[Specialist]:
        """Получить специалиста по user_id."""
        result = await self.session.execute(
            select(Specialist).where(Specialist.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: int, group_id: int, assigned_by: int) -> Specialist:
        """Создать специалиста."""
        specialist = Specialist(user_id=user_id, group_id=group_id, assigned_by=assigned_by)
        self.session.add(specialist)
        await self.session.commit()
        await self.session.refresh(specialist)
        return specialist

    async def delete(self, specialist: Specialist) -> None:
        """Удалить специалиста."""
        await self.session.delete(specialist)
        await self.session.commit()

    async def get_by_group(self, group_id: int) -> List[Specialist]:
        """Получить всех специалистов группы."""
        result = await self.session.execute(
            select(Specialist)
            .options(selectinload(Specialist.user))
            .where(Specialist.group_id == group_id)
            .join(User, Specialist.user_id == User.id)
            .order_by(User.first_name)
        )
        return list(result.scalars().all())

    async def get_all_with_groups(self) -> List[Specialist]:
        """Получить всех специалистов с информацией о группах."""
        result = await self.session.execute(
            select(Specialist)
            .options(selectinload(Specialist.user), selectinload(Specialist.group))
            .join(Group)
            .join(User)
        )
        return list(result.scalars().all())


class RequestRepository:
    """Репозиторий для работы с заявками."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, text: str) -> Request:
        """Создать новую заявку."""
        request = Request(user_id=user_id, text=text)
        self.session.add(request)
        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def get_by_id(self, request_id: int) -> Optional[Request]:
        """Получить заявку по ID."""
        result = await self.session.execute(
            select(Request)
            .options(selectinload(Request.user))
            .where(Request.id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_by_status(self, status: RequestStatus) -> List[Request]:
        """Получить заявки по статусу."""
        result = await self.session.execute(
            select(Request)
            .where(Request.status == status)
            .order_by(Request.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_all(self) -> List[Request]:
        """Получить все заявки."""
        result = await self.session.execute(
            select(Request).order_by(Request.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_user_requests(self, user_id: int) -> List[Request]:
        """Получить заявки пользователя."""
        result = await self.session.execute(
            select(Request)
            .where(Request.user_id == user_id)
            .order_by(Request.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(
        self, request: Request, status: RequestStatus, **kwargs
    ) -> None:
        """Обновить статус заявки."""
        request.status = status
        for key, value in kwargs.items():
            if hasattr(request, key):
                setattr(request, key, value)
        await self.session.commit()

    async def get_new_requests(self) -> List[Request]:
        """Получить все новые заявки."""
        return await self.get_by_status(RequestStatus.NEW)


class AssignmentRepository:
    """Репозиторий для работы с назначениями заявок."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, request_id: int, specialist_id: int, status: AssignmentStatus = AssignmentStatus.PENDING
    ) -> RequestAssignment:
        """Создать назначение."""
        assignment = RequestAssignment(
            request_id=request_id,
            specialist_id=specialist_id,
            status=status,
        )
        self.session.add(assignment)
        await self.session.commit()
        await self.session.refresh(assignment)
        return assignment

    async def get_by_request(self, request_id: int) -> List[RequestAssignment]:
        """Получить все назначения заявки."""
        result = await self.session.execute(
            select(RequestAssignment).where(RequestAssignment.request_id == request_id)
        )
        return list(result.scalars().all())

    async def get_pending_by_specialist(self, specialist_id: int) -> List[RequestAssignment]:
        """Получить ожидающие назначения для специалиста."""
        result = await self.session.execute(
            select(RequestAssignment)
            .where(
                RequestAssignment.specialist_id == specialist_id,
                RequestAssignment.status == AssignmentStatus.PENDING,
            )
            .join(Request)
            .order_by(Request.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(
        self, assignment: RequestAssignment, status: AssignmentStatus, **kwargs
    ) -> None:
        """Обновить статус назначения."""
        assignment.status = status
        for key, value in kwargs.items():
            if hasattr(assignment, key):
                setattr(assignment, key, value)
        await self.session.commit()

    async def cancel_other_assignments(
        self, request_id: int, exclude_specialist_id: int
    ) -> None:
        """Отменить все назначения кроме указанного."""
        await self.session.execute(
            RequestAssignment.__table__
            .update()
            .where(
                RequestAssignment.request_id == request_id,
                RequestAssignment.specialist_id != exclude_specialist_id,
                RequestAssignment.status == AssignmentStatus.PENDING,
            )
            .values(status=AssignmentStatus.CANCELLED)
        )
        await self.session.commit()
