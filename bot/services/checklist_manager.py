from typing import List, Optional
from sqlalchemy.orm import Session
from bot.models.database import Checklist, Task, get_db

class ChecklistManager:
    """Управление чек-листами"""

    def __init__(self):
        self.db_gen = get_db()
        self.db = next(self.db_gen)

    def create_checklist(self, user_id: int, title: str, tasks: List[str]) -> Checklist:
        """Создает новый чек-лист в базе данных"""
        checklist = Checklist(
            user_id=user_id,
            title=title,
            message_id=0  # Будет установлен после отправки
        )
        self.db.add(checklist)
        self.db.commit()
        self.db.refresh(checklist)

        # Добавляем задачи
        for i, task_text in enumerate(tasks):
            task = Task(
                checklist_id=checklist.id,
                text=task_text,
                position=i
            )
            self.db.add(task)

        self.db.commit()
        return checklist

    def get_checklist(self, checklist_id: int) -> Optional[Checklist]:
        """Получает чек-лист по ID"""
        return self.db.query(Checklist).filter(Checklist.id == checklist_id).first()

    def get_user_checklists(self, user_id: int) -> List[Checklist]:
        """Получает все чек-листы пользователя"""
        return self.db.query(Checklist).filter(Checklist.user_id == user_id).all()

    def update_task_status(self, task_id: int, completed: bool) -> bool:
        """Обновляет статус задачи"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.completed = completed
            self.db.commit()
            return True
        return False

    def delete_checklist(self, checklist_id: int, user_id: int) -> bool:
        """Удаляет чек-лист"""
        checklist = self.db.query(Checklist).filter(
            Checklist.id == checklist_id,
            Checklist.user_id == user_id
        ).first()
        if checklist:
            # Удаляем связанные задачи
            self.db.query(Task).filter(Task.checklist_id == checklist_id).delete()
            # Удаляем чек-лист
            self.db.delete(checklist)
            self.db.commit()
            return True
        return False