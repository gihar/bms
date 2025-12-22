from aiogram import Router, types, F
from aiogram.types import ReplyParameters, InputChecklistTask, InputChecklist
from bot.services.checklist_manager import ChecklistManager
from bot.services.business_connection_service import BusinessConnectionService
from bot.services.user_whitelist_service import UserWhitelistService
from bot.services.parser import TextParser
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = Router()
checklist_manager = ChecklistManager()
business_service = BusinessConnectionService()
whitelist_service = UserWhitelistService()

@router.business_connection()
async def handle_business_connection(connection: types.BusinessConnection):
    """Получаем business_connection_id при подключении"""
    try:
        logger.info(f"Получен business_connection_id: {connection.id}")
        logger.info(f"Детали соединения: {connection}")
        logger.info(f"Пользователь: {connection.user.id if connection.user else 'Unknown'}")
        logger.info(f"Дата: {connection.date}")
        
        # Сохраняем соединение в базу данных
        user_id = connection.user.id if connection.user else 0
        business_service.save_connection(connection.id, user_id)
        
        logger.info(f"✅ Бизнес-соединение успешно сохранено: {connection.id}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке бизнес-соединения: {e}")
        import traceback
        traceback.print_exc()

@router.business_message(F.text)
async def handle_business_message(message: types.Message):
    """Обрабатывает текстовые бизнес-сообщения и создает чек-листы"""
    try:
        logger.info(f"Получено бизнес-сообщение: {message.text}")
        logger.info(f"Business connection ID: {message.business_connection_id}")
        logger.info(f"Chat ID: {message.chat.id}")
        username = message.from_user.username if message.from_user else None
        user_id = message.from_user.id if message.from_user else None
        logger.info(f"От пользователя: @{username} (ID: {user_id})")

        # Проверяем, есть ли пользователь в whitelist (по username или user_id)
        logger.info(f"🔍 Проверка whitelist: username='{username}', user_id={user_id}")
        all_users = whitelist_service.get_all_users()
        logger.info(f"📋 Текущий whitelist: {all_users}")

        is_allowed = whitelist_service.is_user_allowed(username, user_id)
        logger.info(f"✅ Результат проверки: {is_allowed}")
        
        if not is_allowed:
            logger.warning(f"❌ Пользователь @{username} (ID: {user_id}) НЕ в whitelist, сообщение игнорируется")
            return
        
        # Парсим текст для получения задач
        tasks = TextParser.parse_text(message.text)
        logger.info(f"Распарсенные задачи: {tasks}")

        if len(tasks) < 2:
            # Если слишком мало задач, просто выходим без ответа
            return

        # Генерируем заголовок
        title = TextParser.generate_title(tasks)
        logger.info(f"Заголовок: {title}")

        # Создаем чек-лист в базе данных
        checklist = checklist_manager.create_checklist(
            user_id=message.from_user.id,
            title=title,
            tasks=tasks
        )
        logger.info(f"Чек-лист создан с ID: {checklist.id}")

        # Создаем список задач для Telegram чек-листа
        checklist_tasks = []
        for i, task_text in enumerate(tasks, start=1):
            # Обрезаем текст задачи до 100 символов (лимит Telegram API)
            truncated_text = task_text[:100] if len(task_text) > 100 else task_text
            checklist_tasks.append(InputChecklistTask(
                id=str(i),
                text=truncated_text
            ))

        # Создаем заголовок с датой и временем
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        title_with_date = f"Список от {now}"

        # Создаем InputChecklist
        input_checklist = InputChecklist(
            title=title_with_date,
            tasks=checklist_tasks,
            others_can_add_tasks=False,
            others_can_mark_tasks_as_done=True
        )

        # Отправляем нативный Telegram чек-лист через бизнес-соединение
        logger.info(f"Отправка нативного чек-листа как ответ на сообщение {message.message_id}")

        sent_message = await message.bot.send_checklist(
            business_connection_id=message.business_connection_id,
            chat_id=message.chat.id,
            checklist=input_checklist,
            reply_parameters=ReplyParameters(message_id=message.message_id)
        )
        logger.info(f"✅ Нативный чек-лист отправлен с ID: {sent_message.message_id}")

        # Обновляем message_id в базе данных
        checklist.message_id = sent_message.message_id
        checklist_manager.db.commit()

    except Exception as e:
        logger.error(f"Ошибка при обработке бизнес-сообщения: {e}")
        import traceback
        traceback.print_exc()
        await message.answer(
            f"❌ Произошла ошибка при создании чек-листа: {str(e)}"
        )