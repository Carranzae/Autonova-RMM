"""
Autonova RMM - Server Configuration
"""

import os
from datetime import timedelta


class Settings:
    """Server configuration settings."""
    
    # Server
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 8000))
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite+aiosqlite:///./autonova.db')
    
    # Redis (for pub/sub and caching)
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET', 'autonova-jwt-secret-change-in-production')
    JWT_ALGORITHM = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRE = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRE = timedelta(days=7)
    
    # Encryption
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', 'autonova-rmm-default-key-change-in-production')
    
    # Agent settings
    HEARTBEAT_TIMEOUT = 90  # seconds - mark agent offline if no heartbeat
    COMMAND_TIMEOUT = 300  # seconds - default command timeout


settings = Settings()
