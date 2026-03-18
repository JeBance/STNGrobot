#!/bin/bash
# Скрипт запуска бота

set -e

# Активируем виртуальное окружение
source venv/bin/activate

# Запускаем бота
echo "🚀 Запуск бота STNGrobot..."
python -m bot.main
