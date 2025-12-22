import asyncio
import logging
import sys
import os
from typing import Any, Callable, Awaitable
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Update

# Добавляем корневую директорию в Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.utils.config import BOT_TOKEN
from bot.models.database import init_db
from bot.handlers import message_handler, callback_handler
from bot.services.business_connection_service import BusinessConnectionService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DebugMiddleware(BaseMiddleware):
    """Middleware для логирования всех входящих обновлений"""
    
    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any]
    ) -> Any:
        logger.info("=" * 60)
        logger.info("ПОЛУЧЕНО ОБНОВЛЕНИЕ")
        
        if hasattr(event, 'business_message') and event.business_message:
            msg = event.business_message
            logger.info("ЭТО БИЗНЕС-СООБЩЕНИЕ!")
            logger.info(f"   Business connection ID: {msg.business_connection_id}")
            logger.info(f"   Chat ID: {msg.chat.id}")
            logger.info(f"   Chat type: {msg.chat.type}")
            logger.info(f"   Text: {msg.text}")
        elif hasattr(event, 'message') and event.message:
            msg = event.message
            logger.info("ЭТО ОБЫЧНОЕ СООБЩЕНИЕ (не бизнес)")
            logger.info(f"   Chat ID: {msg.chat.id}")
            logger.info(f"   Chat type: {msg.chat.type}")
            logger.info(f"   Business connection ID: {msg.business_connection_id}")
            logger.info(f"   Text: {msg.text}")
        else:
            logger.info(f"   Тип события: {type(event).__name__}")
        
        logger.info("=" * 60)
        
        return await handler(event, data)


async def main():
    """Основная функция запуска бота"""
    # Инициализация бота
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )

    # Создание диспетчера
    dp = Dispatcher()
    
    # Добавляем middleware для диагностики
    dp.update.outer_middleware(DebugMiddleware())

    # Инициализация базы данных
    logger.info("Инициализация базы данных...")
    init_db()
    logger.info("✅ База данных инициализирована")

    # Проверка статуса бизнес-соединения
    logger.info("Проверка статуса бизнес-соединения...")
    business_service = BusinessConnectionService()
    connection_info = business_service.get_connection_info()
    
    if connection_info:
        logger.info(f"✅ Найдено активное бизнес-соединение:")
        logger.info(f"   - Connection ID: {connection_info['connection_id']}")
        logger.info(f"   - User ID: {connection_info['user_id']}")
        logger.info(f"   - Подключено: {connection_info['connected_at']}")
        logger.info(f"   - Обновлено: {connection_info['updated_at']}")
    else:
        logger.warning("⚠️  Активное бизнес-соединение не найдено")
        logger.warning("   Бот будет ожидать подключения к бизнес-аккаунту")

    # Подключаем роутеры
    dp.include_router(message_handler.router)
    dp.include_router(callback_handler.router)

    # Запуск бота
    logger.info("🚀 Запуск бота...")
    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message", "business_message", "business_connection", "edited_message", "callback_query"]
        )
    finally:
        logger.info("Остановка бота...")
        await bot.session.close()
        logger.info("✅ Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())