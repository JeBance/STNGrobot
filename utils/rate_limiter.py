"""
Утилиты для ограничения частоты запросов (rate limiting).
"""
import time
from collections import defaultdict
from typing import Dict, List
from datetime import datetime, timedelta


class RateLimiter:
    """Ограничитель частоты запросов для пользователей."""
    
    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        """
        Инициализация ограничителя.
        
        :param max_requests: Максимальное количество запросов в окно времени
        :param window_seconds: Размер окна времени в секундах
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[int, List[float]] = defaultdict(list)
    
    def is_allowed(self, user_id: int) -> bool:
        """
        Проверка, разрешён ли запрос пользователю.
        
        :param user_id: ID пользователя
        :return: True если запрос разрешён, False если превышен лимит
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        # Очищаем старые запросы за пределами окна
        self._requests[user_id] = [
            ts for ts in self._requests[user_id] 
            if ts > window_start
        ]
        
        # Проверяем лимит
        if len(self._requests[user_id]) >= self.max_requests:
            return False
        
        # Добавляем текущий запрос
        self._requests[user_id].append(now)
        return True
    
    def get_remaining_time(self, user_id: int) -> int:
        """
        Получить время до следующего разрешённого запроса.
        
        :param user_id: ID пользователя
        :return: Время в секундах до следующего разрешённого запроса
        """
        if not self._requests[user_id]:
            return 0
        
        now = time.time()
        oldest_request = min(self._requests[user_id])
        window_start = now - self.window_seconds
        
        if oldest_request <= window_start:
            return 0
        
        return int(oldest_request + self.window_seconds - now)


# Глобальный экземпляр для заявок
request_limiter = RateLimiter(max_requests=5, window_seconds=60)
