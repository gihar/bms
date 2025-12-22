from typing import List, Optional, Tuple, Union
from sqlalchemy import or_
from bot.models.database import AllowedUser, BusinessConnection, SessionLocal
import logging

logger = logging.getLogger(__name__)


class UserWhitelistService:
    """Сервис управления списком разрешённых пользователей"""

    def __init__(self):
        self.db = SessionLocal()

    def _parse_identifier(self, identifier: str) -> Tuple[Optional[str], Optional[int]]:
        """Определяет тип идентификатора: username или user_id
        
        Returns:
            (username, None) если это username
            (None, user_id) если это числовой ID
        """
        identifier = identifier.strip().lstrip('@')
        
        # Если состоит только из цифр - это user_id
        if identifier.isdigit():
            return None, int(identifier)
        
        # Иначе это username
        return identifier.lower(), None

    def add_user(self, identifier: str, added_by: int) -> Tuple[bool, str]:
        """Добавляет пользователя в whitelist
        
        Args:
            identifier: @username или числовой user_id
            added_by: user_id того, кто добавляет
            
        Returns:
            (success, message) - результат и сообщение
        """
        username, user_id = self._parse_identifier(identifier)
        
        # Проверяем, есть ли уже
        if username:
            existing = self.db.query(AllowedUser).filter(
                AllowedUser.username == username
            ).first()
            display_name = f"@{username}"
        else:
            existing = self.db.query(AllowedUser).filter(
                AllowedUser.telegram_user_id == user_id
            ).first()
            display_name = f"ID:{user_id}"
        
        if existing:
            return False, f"Пользователь {display_name} уже в списке"
        
        user = AllowedUser(
            username=username,
            telegram_user_id=user_id,
            added_by=added_by
        )
        self.db.add(user)
        self.db.commit()
        logger.info(f"Пользователь {display_name} добавлен в whitelist")
        return True, f"Пользователь {display_name} добавлен в список"

    def remove_user(self, identifier: str) -> Tuple[bool, str]:
        """Удаляет пользователя из whitelist
        
        Args:
            identifier: @username или числовой user_id
            
        Returns:
            (success, message) - результат и сообщение
        """
        username, user_id = self._parse_identifier(identifier)
        
        if username:
            user = self.db.query(AllowedUser).filter(
                AllowedUser.username == username
            ).first()
            display_name = f"@{username}"
        else:
            user = self.db.query(AllowedUser).filter(
                AllowedUser.telegram_user_id == user_id
            ).first()
            display_name = f"ID:{user_id}"
        
        if not user:
            return False, f"Пользователь {display_name} не найден в списке"
        
        self.db.delete(user)
        self.db.commit()
        logger.info(f"Пользователь {display_name} удалён из whitelist")
        return True, f"Пользователь {display_name} удалён из списка"

    def get_all_users(self) -> List[str]:
        """Возвращает список всех пользователей в whitelist
        
        Returns:
            Список строк вида "@username" или "ID:123456"
        """
        users = self.db.query(AllowedUser).order_by(AllowedUser.added_at).all()
        result = []
        for user in users:
            if user.username:
                result.append(f"@{user.username}")
            elif user.telegram_user_id:
                result.append(f"ID:{user.telegram_user_id}")
        return result

    def is_user_allowed(self, username: Optional[str], user_id: Optional[int] = None) -> bool:
        """Проверяет, есть ли пользователь в whitelist
        
        Args:
            username: имя пользователя (без @), может быть None
            user_id: числовой ID пользователя, может быть None
            
        Returns:
            True если пользователь в списке
        """
        conditions = []
        
        if username:
            conditions.append(AllowedUser.username == username.lower())
        
        if user_id:
            conditions.append(AllowedUser.telegram_user_id == user_id)
        
        if not conditions:
            return False
        
        exists = self.db.query(AllowedUser).filter(
            or_(*conditions)
        ).first() is not None
        
        return exists

    def get_owner_id(self) -> Optional[int]:
        """Получает user_id владельца бота (из активного бизнес-соединения)"""
        connection = self.db.query(BusinessConnection).filter(
            BusinessConnection.is_active == True
        ).first()
        
        if connection:
            return connection.user_id
        return None

    def is_owner(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь владельцем бота"""
        owner_id = self.get_owner_id()
        return owner_id is not None and owner_id == user_id
