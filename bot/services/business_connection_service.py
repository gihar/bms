from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional
from bot.models.database import BusinessConnection, SessionLocal
import logging

logger = logging.getLogger(__name__)


class BusinessConnectionService:
    """Сервис для управления бизнес-соединениями"""
    
    def __init__(self):
        self.db: Session = SessionLocal()
    
    def save_connection(self, connection_id: str, user_id: int) -> BusinessConnection:
        """
        Сохраняет новое бизнес-соединение или обновляет существующее
        
        Args:
            connection_id: ID бизнес-соединения из Telegram
            user_id: ID пользователя-владельца бизнес-аккаунта
            
        Returns:
            Объект BusinessConnection
        """
        try:
            # Проверяем, есть ли уже такое соединение
            existing = self.db.query(BusinessConnection).filter(
                BusinessConnection.connection_id == connection_id
            ).first()
            
            if existing:
                # Обновляем существующее соединение
                existing.user_id = user_id
                existing.is_active = True
                existing.updated_at = datetime.utcnow()
                logger.info(f"Обновлено бизнес-соединение: {connection_id}")
            else:
                # Деактивируем все старые соединения (поддержка только одного активного)
                self.db.query(BusinessConnection).update({"is_active": False})
                
                # Создаем новое соединение
                existing = BusinessConnection(
                    connection_id=connection_id,
                    user_id=user_id,
                    is_active=True
                )
                self.db.add(existing)
                logger.info(f"Создано новое бизнес-соединение: {connection_id}")
            
            self.db.commit()
            self.db.refresh(existing)
            return existing
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Ошибка при сохранении бизнес-соединения: {e}")
            raise
    
    def get_active_connection(self) -> Optional[str]:
        """
        Получает ID активного бизнес-соединения
        
        Returns:
            connection_id или None, если активного соединения нет
        """
        try:
            connection = self.db.query(BusinessConnection).filter(
                BusinessConnection.is_active == True
            ).first()
            
            if connection:
                logger.debug(f"Найдено активное соединение: {connection.connection_id}")
                return connection.connection_id
            else:
                logger.debug("Активное бизнес-соединение не найдено")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при получении активного соединения: {e}")
            return None
    
    def deactivate_connection(self, connection_id: str = None) -> bool:
        """
        Деактивирует бизнес-соединение
        
        Args:
            connection_id: ID соединения для деактивации. 
                          Если None, деактивирует все активные соединения.
        
        Returns:
            True если соединение было деактивировано, False иначе
        """
        try:
            if connection_id:
                # Деактивируем конкретное соединение
                result = self.db.query(BusinessConnection).filter(
                    BusinessConnection.connection_id == connection_id
                ).update({"is_active": False, "updated_at": datetime.utcnow()})
                logger.info(f"Деактивировано соединение: {connection_id}")
            else:
                # Деактивируем все активные соединения
                result = self.db.query(BusinessConnection).filter(
                    BusinessConnection.is_active == True
                ).update({"is_active": False, "updated_at": datetime.utcnow()})
                logger.info("Деактивированы все активные соединения")
            
            self.db.commit()
            return result > 0
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Ошибка при деактивации соединения: {e}")
            return False
    
    def update_connection(self, connection_id: str, user_id: int) -> Optional[BusinessConnection]:
        """
        Обновляет существующее бизнес-соединение
        
        Args:
            connection_id: ID бизнес-соединения
            user_id: Новый ID пользователя
            
        Returns:
            Обновленный объект BusinessConnection или None
        """
        try:
            connection = self.db.query(BusinessConnection).filter(
                BusinessConnection.connection_id == connection_id
            ).first()
            
            if connection:
                connection.user_id = user_id
                connection.is_active = True
                connection.updated_at = datetime.utcnow()
                self.db.commit()
                self.db.refresh(connection)
                logger.info(f"Обновлено соединение {connection_id} для пользователя {user_id}")
                return connection
            else:
                logger.warning(f"Соединение {connection_id} не найдено для обновления")
                return None
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Ошибка при обновлении соединения: {e}")
            return None
    
    def get_connection_info(self) -> Optional[dict]:
        """
        Получает информацию об активном соединении
        
        Returns:
            Словарь с информацией о соединении или None
        """
        try:
            connection = self.db.query(BusinessConnection).filter(
                BusinessConnection.is_active == True
            ).first()
            
            if connection:
                return {
                    "connection_id": connection.connection_id,
                    "user_id": connection.user_id,
                    "connected_at": connection.connected_at,
                    "updated_at": connection.updated_at
                }
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации о соединении: {e}")
            return None
    
    def __del__(self):
        """Закрываем сессию при удалении объекта"""
        if hasattr(self, 'db'):
            self.db.close()

