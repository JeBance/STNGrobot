"""
Middleware для сессии базы данных.
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для предоставления сессии БД в хендлеры."""

    def __init__(self, session_getter: Callable[[], AsyncSession]):
        self.session_getter = session_getter

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        async with self.session_getter() as session:
            data["session"] = session
            return await handler(event, data)
