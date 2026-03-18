"""
Модуль обработчиков команд бота.
"""
from .start import router as start_router
from .admin import router as admin_router
from .user import router as user_router
from .specialist import router as specialist_router
from .callbacks import router as callback_router

__all__ = [
    "start_router",
    "admin_router",
    "user_router",
    "specialist_router",
    "callback_router",
]
