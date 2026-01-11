"""
Autonova RMM - Database Models
SQLAlchemy models for persistence.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from config import settings

# Create async engine
engine = create_async_engine(settings.DATABASE_URL, echo=False)

# Create async session factory
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Base class for models
Base = declarative_base()


class User(Base):
    """Admin user model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="user")  # user, admin
    disabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)


class Agent(Base):
    """Registered agent model."""
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(50), unique=True, index=True, nullable=False)
    hostname = Column(String(100))
    username = Column(String(100))
    os_version = Column(String(100))
    ip_address = Column(String(50))
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime)
    is_online = Column(Boolean, default=False)
    notes = Column(Text)
    
    # Relationships
    sessions = relationship("Session", back_populates="agent")
    command_logs = relationship("CommandLog", back_populates="agent")


class Session(Base):
    """Agent session model."""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), unique=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    socket_id = Column(String(50))
    
    # Relationships
    agent = relationship("Agent", back_populates="sessions")


class CommandLog(Base):
    """Command execution log."""
    __tablename__ = "command_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    command_id = Column(String(50), unique=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    command_type = Column(String(50))  # health_check, deep_clean, etc.
    params = Column(JSON)
    status = Column(String(20))  # pending, running, completed, error
    result = Column(JSON)
    error_message = Column(Text)
    issued_by = Column(String(50))
    issued_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Relationships
    agent = relationship("Agent", back_populates="command_logs")


class AuditLog(Base):
    """System audit log."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(50))  # login, command_sent, agent_registered, etc.
    resource_type = Column(String(50))  # user, agent, command
    resource_id = Column(String(50))
    details = Column(JSON)
    ip_address = Column(String(50))


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Get database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
