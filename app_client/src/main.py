"""
Autonova RMM - Client Agent Entry Point (Production Ready)
Main executable for the Windows agent with absolute imports for PyInstaller.
"""

import asyncio
import logging
import sys
import os
import signal
from datetime import datetime
from pathlib import Path

# Fix imports for PyInstaller
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    BASE_DIR = Path(sys._MEIPASS)
    sys.path.insert(0, str(BASE_DIR))
else:
    # Running as script
    BASE_DIR = Path(__file__).parent.parent
    sys.path.insert(0, str(BASE_DIR))
    sys.path.insert(0, str(BASE_DIR / 'src'))

# Now import local modules with try/except for flexibility
try:
    from src.config import Config
    from src.network import create_socket_client, SocketManager
    from src.security import is_admin, elevate_privileges, get_security_status
except ImportError:
    from config import Config
    from network import create_socket_client, SocketManager
    from security import is_admin, elevate_privileges, get_security_status


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('autonova')


class AutonovaAgent:
    """Main agent controller class with production-grade connection stability."""
    
    def __init__(self):
        """Initialize the agent."""
        self.socket_manager: SocketManager = None
        self.running = False
        self.offline_mode = False
        self.autonomous = None
        
        # Connection stability settings
        self.max_reconnect_attempts = 100  # Keep trying for a long time
        self.base_reconnect_delay = 5  # Start with 5 seconds
        self.max_reconnect_delay = 120  # Max 2 minutes between retries
        self.connection_timeout = 30  # 30 second connection timeout
    
    async def start(self):
        """Start the agent."""
        logger.info("=" * 50)
        logger.info("Autonova RMM Agent Starting")
        logger.info("=" * 50)
        
        # Load configuration
        Config.load()
        logger.info(f"Agent ID: {Config.AGENT_ID}")
        logger.info(f"Server: {Config.SERVER_URL}")
        
        # Check security status
        security = get_security_status()
        logger.info(f"Running as admin: {security['is_admin']}")
        
        if security['debugger_attached'] or security['remote_debugger']:
            logger.warning("Debugger detected!")
        
        if security['vm_detected']:
            logger.info("Virtual machine environment detected")
        
        if not security['is_admin']:
            logger.warning("Not running with admin privileges - some features may be limited")
        
        # Initialize autonomous manager
        try:
            from src.core.autonomous_manager import get_autonomous_manager
        except ImportError:
            from core.autonomous_manager import get_autonomous_manager
        self.autonomous = get_autonomous_manager()
        
        # Create socket client
        self.socket_manager = await create_socket_client(
            server_url=Config.SERVER_URL,
            agent_id=Config.AGENT_ID,
            encryption_key=Config.ENCRYPTION_KEY
        )
        
        self.running = True
        
        # Try to connect with retry
        await self._connect_with_retry()
        
        # Main loop
        await self._main_loop()
    
    async def _connect_with_retry(self, max_initial_attempts=5):
        """Try to connect with retries on startup."""
        for attempt in range(1, max_initial_attempts + 1):
            try:
                logger.info(f"Connecting to server... (attempt {attempt}/{max_initial_attempts})")
                await asyncio.wait_for(
                    self.socket_manager.connect(),
                    timeout=self.connection_timeout
                )
                logger.info("✅ Connected to server successfully")
                await self.autonomous.connection_restored(self.socket_manager)
                self.offline_mode = False
                return True
            except asyncio.TimeoutError:
                logger.warning(f"Connection timeout (attempt {attempt})")
            except Exception as e:
                logger.warning(f"Connection failed: {e} (attempt {attempt})")
            
            if attempt < max_initial_attempts:
                delay = min(self.base_reconnect_delay * attempt, 30)
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
        
        logger.error("Could not connect to server after multiple attempts")
        logger.info("Running in AUTONOMOUS mode - will continue trying in background")
        self.offline_mode = True
        await self.autonomous.connection_lost()
        return False
    
    async def _main_loop(self):
        """Main agent loop with intelligent reconnection."""
        reconnect_attempts = 0
        last_autonomous_check = datetime.now()
        consecutive_errors = 0
        
        while self.running:
            try:
                # Check connection status
                if not self.socket_manager.is_connected:
                    if not self.offline_mode:
                        logger.warning("Lost connection to server")
                        await self.autonomous.connection_lost()
                    
                    self.offline_mode = True
                    reconnect_attempts += 1
                    
                    # Calculate smart retry delay (exponential backoff with cap)
                    delay = min(
                        self.base_reconnect_delay * (2 ** min(reconnect_attempts - 1, 5)),
                        self.max_reconnect_delay
                    )
                    
                    logger.info(f"Attempting reconnection in {delay}s... (attempt {reconnect_attempts})")
                    await asyncio.sleep(delay)
                    
                    try:
                        await asyncio.wait_for(
                            self.socket_manager.connect(),
                            timeout=self.connection_timeout
                        )
                        logger.info("✅ Reconnected to server")
                        await self.autonomous.connection_restored(self.socket_manager)
                        self.offline_mode = False
                        reconnect_attempts = 0
                        consecutive_errors = 0
                    except Exception as e:
                        logger.debug(f"Reconnection failed: {e}")
                        
                        # Run autonomous checks only after many failed attempts
                        # and only every 5 minutes to avoid doing too much work
                        if reconnect_attempts >= 10:
                            elapsed = (datetime.now() - last_autonomous_check).seconds
                            if elapsed > 300:  # Every 5 minutes in offline mode
                                logger.info("🤖 Running autonomous health check...")
                                await self._run_autonomous_check()
                                last_autonomous_check = datetime.now()
                else:
                    # Connected - normal operation
                    consecutive_errors = 0
                    await asyncio.sleep(2)  # Check every 2 seconds
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Main loop error: {e}")
                
                # If too many consecutive errors, wait longer
                if consecutive_errors > 5:
                    await asyncio.sleep(30)
                else:
                    await asyncio.sleep(5)
    
    async def _run_autonomous_check(self):
        """Run autonomous health check when offline (conservative mode)."""
        try:
            try:
                from src.core import run_full_scan
                from src.core.autonomous_manager import get_autonomous_manager
            except ImportError:
                from core import run_full_scan
                from core.autonomous_manager import get_autonomous_manager
            
            auto = get_autonomous_manager()
            
            # Just run scan, don't take any automatic actions
            scan_results = await run_full_scan()
            
            # Analyze but DON'T automatically execute
            recommendations = await auto.analyze_and_decide(scan_results)
            
            # Only queue for sync when reconnected - DON'T auto-execute
            auto.queue_for_sync("scan_results", scan_results)
            
            logger.info(f"Autonomous check complete. {len(recommendations)} recommendations queued.")
            
        except Exception as e:
            logger.error(f"Autonomous check error: {e}")
    
    async def stop(self):
        """Stop the agent gracefully."""
        logger.info("Shutting down agent...")
        self.running = False
        
        if self.socket_manager:
            try:
                await self.socket_manager.disconnect()
            except:
                pass
        
        logger.info("Agent stopped")


async def main():
    """Main entry point."""
    agent = AutonovaAgent()
    
    try:
        await agent.start()
    except KeyboardInterrupt:
        await agent.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        await agent.stop()
        sys.exit(1)


def run():
    """Entry point for the agent."""
    # Check for command line arguments
    if '--uninstall' in sys.argv:
        try:
            from src.scripts.self_destruct import initiate_self_destruct
        except ImportError:
            from scripts.self_destruct import initiate_self_destruct
        asyncio.run(initiate_self_destruct())
        return
    
    # Run the agent
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    run()
