from aiogram import Router, types, F
from aiogram.types import ReplyParameters, InputChecklistTask, InputChecklist
from bot.services.checklist_manager import ChecklistManager
from bot.services.business_connection_service import BusinessConnectionService
from bot.services.user_whitelist_service import UserWhitelistService
from bot.services.parser import TextParser
from bot.models.database import PendingMessage, SessionLocal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = Router()
checklist_manager = ChecklistManager()
business_service = BusinessConnectionService()
whitelist_service = UserWhitelistService()


def get_db_session():
    """Возвращает сессию базы данных"""
    return SessionLocal()


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


async def create_checklist_for_message(message: types.Message, original_message: PendingMessage, db):
    """Создаёт чек-лист для сохранённого сообщения"""
    try:
        # Парсим текст для получения задач
        tasks = TextParser.parse_text(original_message.text)
        logger.info(f"Распарсенные задачи: {tasks}")

        if len(tasks) < 2:
            logger.info("Недостаточно задач для создания чек-листа")
            db.delete(original_message)
            db.commit()
            return

        # Генерируем заголовок
        title = TextParser.generate_title(tasks)
        logger.info(f"Заголовок: {title}")

        # Создаем чек-лист в базе данных
        checklist = checklist_manager.create_checklist(
            user_id=original_message.user_id,
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
        logger.info(f"Отправка нативного чек-листа как ответ на сообщение {original_message.message_id}")

        sent_message = await message.bot.send_checklist(
            business_connection_id=original_message.business_connection_id,
            chat_id=original_message.chat_id,
            checklist=input_checklist,
            reply_parameters=ReplyParameters(message_id=original_message.message_id)
        )
        logger.info(f"✅ Нативный чек-лист отправлен с ID: {sent_message.message_id}")

        # Обновляем message_id в базе данных
        checklist.message_id = sent_message.message_id
        checklist_manager.db.commit()
        
        # Удаляем pending message после успешного создания чек-листа
        db.delete(original_message)
        db.commit()
        logger.info("✅ Pending message удалён")

    except Exception as e:
        logger.error(f"Ошибка при создании чек-листа: {e}")
        import traceback
        traceback.print_exc()


@router.business_message(F.text)
async def handle_business_message(message: types.Message):
    """Обрабатывает текстовые бизнес-сообщения"""
    try:
        logger.info(f"Получено бизнес-сообщение: {message.text}")
        logger.info(f"Business connection ID: {message.business_connection_id}")
        logger.info(f"Chat ID: {message.chat.id}")
        logger.info(f"Reply to message: {message.reply_to_message}")
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
        
        # Проверяем, является ли это ответом с эмодзи 📝 или ✍️
        trigger_emojis = ['📝', '✍️', '✍']
        has_trigger = message.reply_to_message and any(emoji in message.text for emoji in trigger_emojis)
        if has_trigger:
            logger.info("✅ Обнаружен ответ с триггер-эмодзи, ищем сохранённое сообщение")
            
            reply_message_id = message.reply_to_message.message_id
            logger.info(f"Reply to message ID: {reply_message_id}")
            
            # Ищем сохранённое сообщение в базе данных
            db = get_db_session()
            try:
                pending = db.query(PendingMessage).filter(
                    PendingMessage.chat_id == message.chat.id,
                    PendingMessage.message_id == reply_message_id
                ).first()
                
                if pending:
                    logger.info(f"✅ Найдено сохранённое сообщение: {pending.text[:50]}...")
                    await create_checklist_for_message(message, pending, db)
                else:
                    logger.warning(f"Сообщение не найдено в pending_messages: chat_id={message.chat.id}, message_id={reply_message_id}")
            finally:
                db.close()
            return
        
        # Парсим текст для проверки количества задач
        tasks = TextParser.parse_text(message.text)
        logger.info(f"Распарсенные задачи: {tasks}")

        if len(tasks) < 2:
            # Если слишком мало задач, просто выходим без сохранения
            logger.info("Недостаточно задач для создания чек-листа, сообщение не сохранено")
            return

        # Сохраняем сообщение в базу данных для ожидания ответа с 📝
        db = get_db_session()
        try:
            pending_message = PendingMessage(
                chat_id=message.chat.id,
                message_id=message.message_id,
                business_connection_id=message.business_connection_id,
                text=message.text,
                user_id=message.from_user.id
            )
            db.add(pending_message)
            db.commit()
            logger.info(f"✅ Сообщение сохранено для ожидания ответа с 📝/✍️: chat_id={message.chat.id}, message_id={message.message_id}")
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Ошибка при обработке бизнес-сообщения: {e}")
        import traceback
        traceback.print_exc()


@router.message_reaction()
async def handle_message_reaction(event: types.MessageReactionUpdated):
    """Обрабатывает реакции на сообщения (на случай если Telegram всё-таки пришлёт)"""
    try:
        logger.info(f"Получена реакция на сообщение")
        logger.info(f"Chat ID: {event.chat.id}")
        logger.info(f"Message ID: {event.message_id}")
        logger.info(f"New reactions: {event.new_reaction}")
        logger.info(f"Old reactions: {event.old_reaction}")
        
        # Проверяем, есть ли эмодзи "📝" или "✍️" в новых реакциях
        trigger_emojis = ['📝', '✍️', '✍']
        has_ok_reaction = False
        for reaction in event.new_reaction:
            if hasattr(reaction, 'emoji') and reaction.emoji in trigger_emojis:
                has_ok_reaction = True
                break
        
        if not has_ok_reaction:
            logger.info("Реакция не является '📝', игнорируем")
            return
        
        logger.info("✅ Обнаружена реакция '📝', ищем сохранённое сообщение")
        
        # Ищем сохранённое сообщение в базе данных
        db = get_db_session()
        try:
            pending = db.query(PendingMessage).filter(
                PendingMessage.chat_id == event.chat.id,
                PendingMessage.message_id == event.message_id
            ).first()
            
            if not pending:
                logger.warning(f"Сообщение не найдено в pending_messages: chat_id={event.chat.id}, message_id={event.message_id}")
                return
            
            logger.info(f"✅ Найдено сохранённое сообщение: {pending.text[:50]}...")
            
            # Создаём фейковый message объект для create_checklist_for_message
            # К сожалению, event не имеет bot атрибута напрямую
            # Поэтому используем альтернативный подход
            
            # Парсим текст для получения задач
            tasks = TextParser.parse_text(pending.text)
            logger.info(f"Распарсенные задачи: {tasks}")

            if len(tasks) < 2:
                logger.info("Недостаточно задач для создания чек-листа")
                db.delete(pending)
                db.commit()
                return

            # Генерируем заголовок
            title = TextParser.generate_title(tasks)
            logger.info(f"Заголовок: {title}")

            # Создаем чек-лист в базе данных
            checklist = checklist_manager.create_checklist(
                user_id=pending.user_id,
                title=title,
                tasks=tasks
            )
            logger.info(f"Чек-лист создан с ID: {checklist.id}")

            # Создаем список задач для Telegram чек-листа
            checklist_tasks = []
            for i, task_text in enumerate(tasks, start=1):
                truncated_text = task_text[:100] if len(task_text) > 100 else task_text
                checklist_tasks.append(InputChecklistTask(
                    id=str(i),
                    text=truncated_text
                ))

            now = datetime.now().strftime("%d.%m.%Y %H:%M")
            title_with_date = f"Список от {now}"

            input_checklist = InputChecklist(
                title=title_with_date,
                tasks=checklist_tasks,
                others_can_add_tasks=False,
                others_can_mark_tasks_as_done=True
            )

            sent_message = await event.bot.send_checklist(
                business_connection_id=pending.business_connection_id,
                chat_id=pending.chat_id,
                checklist=input_checklist,
                reply_parameters=ReplyParameters(message_id=pending.message_id)
            )
            logger.info(f"✅ Нативный чек-лист отправлен с ID: {sent_message.message_id}")

            checklist.message_id = sent_message.message_id
            checklist_manager.db.commit()
            
            db.delete(pending)
            db.commit()
            logger.info("✅ Pending message удалён")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Ошибка при обработке реакции на сообщение: {e}")
        import traceback
        traceback.print_exc()