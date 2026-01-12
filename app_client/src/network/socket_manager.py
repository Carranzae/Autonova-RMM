"""
Autonova RMM - Socket Manager
WebSocket client with automatic reconnection and AES-256 encryption.
Handles JSON command reception and execution with heartbeat system.
"""

import asyncio
import json
import logging
import os
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from enum import Enum

import socketio
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Socket connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


class AESCipher:
    """AES-256 encryption for secure message transmission."""
    
    def __init__(self, key: str):
        """
        Initialize cipher with key.
        
        Args:
            key: Encryption key (will be hashed to 256 bits)
        """
        self.key = hashlib.sha256(key.encode()).digest()
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt data using AES-256-CBC.
        
        Args:
            data: Plain text to encrypt
            
        Returns:
            Base64 encoded encrypted string (iv + ciphertext)
        """
        iv = get_random_bytes(16)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        padded_data = pad(data.encode('utf-8'), AES.block_size)
        encrypted = cipher.encrypt(padded_data)
        return base64.b64encode(iv + encrypted).decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt AES-256-CBC encrypted data.
        
        Args:
            encrypted_data: Base64 encoded encrypted string
            
        Returns:
            Decrypted plain text
        """
        raw = base64.b64decode(encrypted_data)
        iv = raw[:16]
        ciphertext = raw[16:]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return decrypted.decode('utf-8')


class SocketManager:
    """
    WebSocket client manager with auto-reconnect and encryption.
    
    Handles bidirectional communication with the C&C server.
    """
    
    def __init__(
        self,
        server_url: str,
        agent_id: str,
        encryption_key: str,
        command_handler: Optional[Callable] = None
    ):
        """
        Initialize the socket manager.
        
        Args:
            server_url: WebSocket server URL (wss://...)
            agent_id: Unique identifier for this agent
            encryption_key: Key for AES-256 encryption
            command_handler: Async function to handle incoming commands
        """
        self.server_url = server_url
        self.agent_id = agent_id
        self.cipher = AESCipher(encryption_key)
        self.command_handler = command_handler
        
        # Socket.IO client with reconnection settings
        self.sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=0,  # Infinite attempts
            reconnection_delay=1,
            reconnection_delay_max=30,
            randomization_factor=0.5,
            logger=False,
            engineio_logger=False
        )
        
        # State tracking
        self.state = ConnectionState.DISCONNECTED
        self.last_heartbeat = None
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.pending_responses: Dict[str, asyncio.Future] = {}
        
        # Register event handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register Socket.IO event handlers."""
        
        @self.sio.on('connect', namespace='/agents')
        async def on_connect():
            """Handle successful connection."""
            logger.info(f"Connected to server: {self.server_url}")
            self.state = ConnectionState.CONNECTED
            
            # Send authentication/registration
            await self._send_auth()
            
            # Start heartbeat
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        @self.sio.on('disconnect', namespace='/agents')
        async def on_disconnect():
            """Handle disconnection."""
            logger.warning("Disconnected from server")
            self.state = ConnectionState.DISCONNECTED
            
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
        
        @self.sio.on('connect_error', namespace='/agents')
        async def on_connect_error(data):
            """Handle connection errors."""
            logger.error(f"Connection error: {data}")
            self.state = ConnectionState.DISCONNECTED
        
        @self.sio.on('command', namespace='/agents')
        async def on_command(encrypted_data: str):
            """
            Handle incoming encrypted command.
            
            Expected JSON structure:
            {
                "id": "cmd_uuid",
                "type": "health_check|deep_clean|sys_fix|full_optimize",
                "params": {...}
            }
            """
            try:
                # Decrypt the command
                decrypted = self.cipher.decrypt(encrypted_data)
                command = json.loads(decrypted)
                
                logger.info(f"Received command: {command.get('type')}")
                
                # Execute command handler
                if self.command_handler:
                    result = await self.command_handler(command)
                    
                    # Send response back
                    await self.send_response(command.get('id'), result)
                    
            except Exception as e:
                logger.error(f"Command processing error: {e}")
                await self.send_error(
                    command.get('id') if 'command' in dir() else None,
                    str(e)
                )
        
        @self.sio.on('response', namespace='/agents')
        async def on_response(encrypted_data: str):
            """Handle response to a previous request."""
            try:
                decrypted = self.cipher.decrypt(encrypted_data)
                response = json.loads(decrypted)
                
                # Resolve pending future if exists
                cmd_id = response.get('command_id')
                if cmd_id in self.pending_responses:
                    self.pending_responses[cmd_id].set_result(response)
                    del self.pending_responses[cmd_id]
                    
            except Exception as e:
                logger.error(f"Response processing error: {e}")
        
        @self.sio.on('ping', namespace='/agents')
        async def on_ping():
            """Respond to server ping."""
            await self.sio.emit('pong', {'agent_id': self.agent_id}, namespace='/agents')
    
    async def _send_auth(self):
        """Send authentication message to server."""
        auth_data = {
            "agent_id": self.agent_id,
            "hostname": os.environ.get('COMPUTERNAME', 'unknown'),
            "username": os.environ.get('USERNAME', 'unknown'),
            "timestamp": datetime.now().isoformat()
        }
        
        encrypted = self.cipher.encrypt(json.dumps(auth_data))
        await self.sio.emit('auth', encrypted, namespace='/agents')
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat to server."""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                if self.state == ConnectionState.CONNECTED:
                    heartbeat = {
                        "agent_id": self.agent_id,
                        "timestamp": datetime.now().isoformat(),
                        "uptime": self._get_uptime()
                    }
                    
                    encrypted = self.cipher.encrypt(json.dumps(heartbeat))
                    await self.sio.emit('heartbeat', encrypted, namespace='/agents')
                    self.last_heartbeat = datetime.now()
                    logger.debug("Heartbeat sent")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
    
    def _get_uptime(self) -> float:
        """Get agent uptime in seconds."""
        try:
            import psutil
            return datetime.now().timestamp() - psutil.boot_time()
        except Exception:
            return 0
    
    async def connect(self):
        """
        Establish connection to the server.
        Auto-reconnect is handled automatically.
        """
        self.state = ConnectionState.CONNECTING
        
        try:
            await self.sio.connect(
                self.server_url,
                transports=['websocket'],
                namespaces=['/agents']
            )
        except Exception as e:
            logger.error(f"Initial connection failed: {e}")
            self.state = ConnectionState.DISCONNECTED
            raise
    
    async def disconnect(self):
        """Gracefully disconnect from server."""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        
        if self.sio.connected:
            await self.sio.disconnect()
        
        self.state = ConnectionState.DISCONNECTED
    
    async def send_progress(self, command_id: str, progress_data: Dict[str, Any]):
        """
        Send progress update for a running command.
        
        Args:
            command_id: ID of the command being executed
            progress_data: Progress information
        """
        message = {
            "command_id": command_id,
            "agent_id": self.agent_id,
            "type": "progress",
            "data": progress_data,
            "timestamp": datetime.now().isoformat()
        }
        
        encrypted = self.cipher.encrypt(json.dumps(message))
        await self.sio.emit('progress', encrypted, namespace='/agents')
    
    async def send_response(self, command_id: str, result: Dict[str, Any]):
        """
        Send command execution result.
        
        Args:
            command_id: ID of the completed command
            result: Execution result
        """
        message = {
            "command_id": command_id,
            "agent_id": self.agent_id,
            "type": "result",
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat()
        }
        
        encrypted = self.cipher.encrypt(json.dumps(message))
        await self.sio.emit('result', encrypted, namespace='/agents')
        logger.info(f"Sent result for command: {command_id}")
    
    async def send_error(self, command_id: Optional[str], error: str):
        """
        Send error response.
        
        Args:
            command_id: ID of the failed command
            error: Error message
        """
        message = {
            "command_id": command_id,
            "agent_id": self.agent_id,
            "type": "error",
            "success": False,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
        encrypted = self.cipher.encrypt(json.dumps(message))
        await self.sio.emit('error', encrypted, namespace='/agents')
        logger.error(f"Sent error for command {command_id}: {error}")
    
    async def send_log(self, level: str, message: str):
        """
        Send log message to server.
        
        Args:
            level: Log level (info, warning, error)
            message: Log message
        """
        log_data = {
            "agent_id": self.agent_id,
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        encrypted = self.cipher.encrypt(json.dumps(log_data))
        await self.sio.emit('log', encrypted, namespace='/agents')
    
    async def wait_for_connection(self, timeout: float = 30.0) -> bool:
        """
        Wait for connection to be established.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if connected, False if timeout
        """
        start = datetime.now()
        while (datetime.now() - start).total_seconds() < timeout:
            if self.state == ConnectionState.CONNECTED:
                return True
            await asyncio.sleep(0.1)
        return False
    
    @property
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self.state == ConnectionState.CONNECTED and self.sio.connected


class CommandExecutor:
    """
    Executes commands received from the server.
    Integrates with core modules (health_check, deep_clean, sys_fixer, etc).
    """
    
    def __init__(self, socket_manager: SocketManager):
        """
        Initialize the command executor.
        
        Args:
            socket_manager: Socket manager instance for sending updates
        """
        self.socket_manager = socket_manager
        self.command_logs = []
        self.last_scan_results = {}  # Store last scan results for report
        
        # Import core modules
        from ..core import (
            run_health_check, run_deep_clean, run_sys_fix,
            list_processes, analyze_disk, generate_report,
            run_full_scan
        )
        self.run_health_check = run_health_check
        self.run_deep_clean = run_deep_clean
        self.run_sys_fix = run_sys_fix
        self.list_processes = list_processes
        self.analyze_disk = analyze_disk
        self.generate_report = generate_report
        self.run_full_scan = run_full_scan
    
    async def execute(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a command and return the result.
        
        Args:
            command: Command dict with 'id', 'type', and optional 'params'
            
        Returns:
            Execution result
        """
        cmd_id = command.get('id')
        cmd_type = command.get('type')
        params = command.get('params', {})
        
        # Create progress callback
        async def progress_callback(data):
            await self.socket_manager.send_progress(cmd_id, data)
        
        try:
            result = None
            
            if cmd_type == 'health_check':
                # Use comprehensive system scanner and save results
                result = await self.run_full_scan(progress_callback)
                self.last_scan_results = result  # Save for report
            
            elif cmd_type == 'deep_clean':
                result = await self.run_deep_clean(progress_callback)
            
            elif cmd_type == 'sys_fix':
                result = await self.run_sys_fix(progress_callback)
            
            elif cmd_type == 'full_optimize':
                # Execute all operations in sequence
                result = {
                    "health_check": await self.run_full_scan(progress_callback),
                    "deep_clean": await self.run_deep_clean(progress_callback),
                    "sys_fix": await self.run_sys_fix(progress_callback)
                }
                self.last_scan_results = result.get("health_check", {})
                await progress_callback({"message": "✅ Optimización completa finalizada", "level": "success"})
            
            elif cmd_type == 'view_processes':
                await progress_callback({"message": "📊 Obteniendo lista de procesos...", "percent": 0})
                result = await self.list_processes(progress_callback)
                process_count = len(result.get("processes", []))
                await progress_callback({"message": f"✅ {process_count} procesos encontrados", "level": "success"})
            
            elif cmd_type == 'analyze_disk':
                await progress_callback({"message": "💾 Iniciando análisis de disco...", "percent": 0})
                result = await self.analyze_disk(progress_callback)
                junk_size = result.get("total_junk_size", "0 B")
                await progress_callback({"message": f"✅ Análisis completado: {junk_size} de archivos basura", "level": "success"})
            
            elif cmd_type == 'force_delete':
                await progress_callback({"message": "💪 Iniciando eliminación forzada...", "percent": 0})
                result = await self.run_deep_clean(progress_callback)
                await progress_callback({"message": "✅ Eliminación forzada completada", "level": "success"})
            
            elif cmd_type == 'clean_registry':
                await progress_callback({"message": "📝 Limpiando registro de Windows...", "percent": 0})
                result = await self.run_deep_clean(progress_callback)
                await progress_callback({"message": "✅ Limpieza de registro completada", "level": "success"})
            
            elif cmd_type == 'speed_up_boot':
                await progress_callback({"message": "🚀 Optimizando programas de inicio...", "percent": 0})
                result = await self.run_sys_fix(progress_callback)
                await progress_callback({"message": "✅ Optimización de inicio completada", "level": "success"})
            
            elif cmd_type == 'network_reset':
                await progress_callback({"message": "🌐 Reparando configuración de red...", "percent": 0})
                result = await self.run_sys_fix(progress_callback)
                await progress_callback({"message": "✅ Reset de red completado", "level": "success"})
            
            elif cmd_type == 'generate_report':
                await progress_callback({"message": "📄 Generando reporte profesional...", "percent": 0})
                import os
                hostname = os.environ.get('COMPUTERNAME', 'Unknown')
                result = await self.generate_report(
                    hostname=hostname,
                    agent_id=self.socket_manager.agent_id,
                    command_logs=self.command_logs,
                    scan_results=self.last_scan_results,
                    progress_callback=progress_callback
                )
                await progress_callback({"message": "✅ Reporte generado exitosamente", "level": "success"})
            
            elif cmd_type == 'self_destruct':
                await progress_callback({"message": "⚠️ Desinstalando agente...", "percent": 0})
                try:
                    from ..scripts.self_destruct import initiate_self_destruct
                except ImportError:
                    from scripts.self_destruct import initiate_self_destruct
                result = await initiate_self_destruct(progress_callback)
            
            elif cmd_type == 'force_uninstall':
                program_name = params.get("program_name", "")
                if not program_name:
                    result = {"success": False, "error": "No se especificó el programa"}
                else:
                    await progress_callback({"message": f"🗑️ Desinstalando {program_name}...", "percent": 0})
                    try:
                        from ..scripts.self_destruct import force_uninstall_program
                    except ImportError:
                        from scripts.self_destruct import force_uninstall_program
                    result = await force_uninstall_program(program_name, progress_callback)
            
            elif cmd_type == 'kill_process':
                process_name = params.get("process_name", "")
                if not process_name:
                    result = {"success": False, "error": "No se especificó el proceso"}
                else:
                    await progress_callback({"message": f"🔪 Terminando {process_name}...", "percent": 0})
                    try:
                        from ..scripts.self_destruct import kill_process_by_name
                    except ImportError:
                        from scripts.self_destruct import kill_process_by_name
                    result = await kill_process_by_name(process_name, progress_callback)
            
            elif cmd_type == 'list_programs':
                await progress_callback({"message": "📋 Listando programas instalados...", "percent": 0})
                try:
                    from ..scripts.self_destruct import list_installed_programs
                except ImportError:
                    from scripts.self_destruct import list_installed_programs
                result = await list_installed_programs(progress_callback)
            
            else:
                result = {"error": f"Comando desconocido: {cmd_type}"}
            
            # Log command for report generation
            self.command_logs.append({
                "command_id": cmd_id,
                "command_type": cmd_type,
                "result": result,
                "success": result.get("success", True) if isinstance(result, dict) else True,
                "timestamp": datetime.now().isoformat()
            })
            
            return result
                
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return {"error": str(e), "success": False}


async def create_socket_client(
    server_url: str,
    agent_id: str,
    encryption_key: str
) -> SocketManager:
    """
    Factory function to create and configure a socket client.
    
    Args:
        server_url: WebSocket server URL
        agent_id: Unique agent identifier
        encryption_key: AES encryption key
        
    Returns:
        Configured SocketManager instance
    """
    manager = SocketManager(
        server_url=server_url,
        agent_id=agent_id,
        encryption_key=encryption_key
    )
    
    # Create command executor
    executor = CommandExecutor(manager)
    manager.command_handler = executor.execute
    
    return manager
