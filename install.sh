#!/bin/bash
# Скрипт установки и запуска бота STNGrobot

set -e

echo "🔧 Установка бота STNGrobot..."

# Создаём виртуальное окружение если нет
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активируем виртуальное окружение
source venv/bin/activate

# Устанавливаем зависимости
echo "📦 Установка зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

# Создаём директорию для логов
mkdir -p logs

# Проверяем наличие .env
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден. Копируем из .env.example..."
    cp .env.example .env
    echo "❗ Отредактируйте .env и укажите BOT_TOKEN, ROOT_ID и DATABASE_URL"
    exit 1
fi

# Применяем миграции
echo "🗄 Применение миграций базы данных..."
alembic upgrade head

echo "✅ Установка завершена!"
echo ""
echo "Для запуска бота выполните:"
echo "  source venv/bin/activate"
echo "  python -m bot.main"
