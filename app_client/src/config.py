"""
Autonova RMM - Agent Configuration
"""

import os
import uuid
import json
from pathlib import Path


class Config:
    """Agent configuration settings."""
    
    # Server connection - PRODUCTION URL
    SERVER_URL = os.environ.get('AUTONOVA_SERVER', 'https://autonova-rmm.onrender.com')
    
    # Encryption key (MUST match server's ENCRYPTION_KEY)
    ENCRYPTION_KEY = os.environ.get('AUTONOVA_KEY', 'autonova-rmm-production-key-12345')
    
    # Agent identification
    AGENT_ID = None  # Generated or loaded on startup
    
    # Connection settings
    HEARTBEAT_INTERVAL = 30  # seconds
    RECONNECT_DELAY = 1  # Initial reconnect delay
    RECONNECT_MAX_DELAY = 30  # Maximum reconnect delay
    
    # Operation timeouts (seconds)
    HEALTH_CHECK_TIMEOUT = 120
    DEEP_CLEAN_TIMEOUT = 600
    SYS_FIX_TIMEOUT = 3600
    
    # Paths
    CONFIG_DIR = Path(os.environ.get('LOCALAPPDATA', '')) / 'Autonova'
    LOG_FILE = CONFIG_DIR / 'agent.log'
    CONFIG_FILE = CONFIG_DIR / 'config.json'
    
    @classmethod
    def load(cls):
        """Load configuration from file."""
        cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        # First load from config file (for agent_id only)
        if cls.CONFIG_FILE.exists():
            try:
                with open(cls.CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    cls.AGENT_ID = data.get('agent_id')
                    # Don't load server_url from saved config - use .env instead
            except Exception:
                pass
        
        # Then load from .env file (highest priority for SERVER_URL)
        env_file = Path(__file__).parent.parent / '.env'
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            if key and value:
                                os.environ[key] = value
                # Re-read environment variables
                cls.SERVER_URL = os.environ.get('AUTONOVA_SERVER', cls.SERVER_URL)
                cls.ENCRYPTION_KEY = os.environ.get('AUTONOVA_KEY', cls.ENCRYPTION_KEY)
                print(f"[Config] Loaded from .env: SERVER={cls.SERVER_URL}")
            except Exception as e:
                print(f"[Config] Error loading .env: {e}")
        
        # Generate new agent ID if needed
        if not cls.AGENT_ID:
            cls.AGENT_ID = f"agent_{uuid.uuid4().hex[:12]}"
            cls.save()
    
    @classmethod
    def save(cls):
        """Save configuration to file."""
        cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        data = {
            'agent_id': cls.AGENT_ID,
            'server_url': cls.SERVER_URL
        }
        
        try:
            with open(cls.CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
    
    @classmethod
    def get_agent_id(cls) -> str:
        """Get the agent ID, loading config if needed."""
        if not cls.AGENT_ID:
            cls.load()
        return cls.AGENT_ID
