from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from bot.utils.config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class BusinessConnection(Base):
    __tablename__ = "business_connections"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(String, unique=True, nullable=False)
    user_id = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    connected_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Checklist(Base):
    __tablename__ = "checklists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    message_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    checklist_id = Column(Integer, nullable=False)
    text = Column(String, nullable=False)
    completed = Column(Boolean, default=False)
    position = Column(Integer, nullable=False)

class AllowedUser(Base):
    """Пользователи, для которых бот создаёт чек-листы"""
    __tablename__ = "allowed_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=True)  # без @, может быть None
    telegram_user_id = Column(Integer, unique=True, nullable=True)  # числовой ID пользователя
    added_at = Column(DateTime, default=datetime.utcnow)
    added_by = Column(Integer, nullable=False)  # user_id владельца


class PendingMessage(Base):
    """Сообщения, ожидающие реакции для создания чек-листа"""
    __tablename__ = "pending_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, nullable=False)
    message_id = Column(Integer, nullable=False)
    business_connection_id = Column(String, nullable=False)
    text = Column(String, nullable=False)
    user_id = Column(Integer, nullable=False)  # ID отправителя сообщения
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()