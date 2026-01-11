"""
Autonova RMM - Agent Socket Namespace
Handles WebSocket communication with agents.
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from base64 import b64decode, b64encode

import socketio
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

from config import settings

# Connected agents store
connected_agents: Dict[str, Dict[str, Any]] = {}

# Pending commands store
pending_commands: Dict[str, Dict[str, Any]] = {}


class AESCipher:
    """AES-256 encryption for secure message transmission."""
    
    def __init__(self, key: str):
        self.key = hashlib.sha256(key.encode()).digest()
    
    def encrypt(self, data: str) -> str:
        iv = get_random_bytes(16)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        padded_data = pad(data.encode('utf-8'), AES.block_size)
        encrypted = cipher.encrypt(padded_data)
        return b64encode(iv + encrypted).decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> str:
        raw = b64decode(encrypted_data)
        iv = raw[:16]
        ciphertext = raw[16:]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return decrypted.decode('utf-8')


cipher = AESCipher(settings.ENCRYPTION_KEY)

# Store sio reference globally
_sio_instance = None


def set_sio_instance(sio):
    global _sio_instance
    _sio_instance = sio


class AgentNamespace(socketio.AsyncNamespace):
    """Socket.IO namespace for agent connections."""
    
    def __init__(self, namespace: str, sio: socketio.AsyncServer):
        super().__init__(namespace)
        self.sio = sio
        set_sio_instance(sio)
    
    async def on_connect(self, sid: str, environ: dict):
        """Handle agent connection."""
        print(f"Agent connecting: {sid}")
    
    async def on_disconnect(self, sid: str):
        """Handle agent disconnection."""
        # Find and mark agent as offline
        for agent_id, info in connected_agents.items():
            if info.get("sid") == sid:
                info["online"] = False
                info["disconnected_at"] = datetime.now().isoformat()
                print(f"Agent disconnected: {agent_id}")
                break
    
    async def on_auth(self, sid: str, encrypted_data: str):
        """Handle agent authentication."""
        try:
            decrypted = cipher.decrypt(encrypted_data)
            auth_data = json.loads(decrypted)
            
            agent_id = auth_data.get("agent_id")
            if not agent_id:
                await self.disconnect(sid)
                return
            
            # Register agent
            connected_agents[agent_id] = {
                "sid": sid,
                "agent_id": agent_id,
                "hostname": auth_data.get("hostname"),
                "username": auth_data.get("username"),
                "connected_at": datetime.now().isoformat(),
                "last_heartbeat": datetime.now().isoformat(),
                "online": True,
                "command_logs": []
            }
            
            print(f"Agent authenticated: {agent_id} ({auth_data.get('hostname')})")
            
            # Send acknowledgment
            await self.emit('auth_ack', {'status': 'ok'}, to=sid)
            
        except Exception as e:
            print(f"Auth error: {e}")
            await self.disconnect(sid)
    
    async def on_heartbeat(self, sid: str, encrypted_data: str):
        """Handle agent heartbeat."""
        try:
            decrypted = cipher.decrypt(encrypted_data)
            heartbeat = json.loads(decrypted)
            
            agent_id = heartbeat.get("agent_id")
            if agent_id in connected_agents:
                connected_agents[agent_id]["last_heartbeat"] = datetime.now().isoformat()
                connected_agents[agent_id]["online"] = True
                
        except Exception as e:
            print(f"Heartbeat error: {e}")
    
    async def on_progress(self, sid: str, encrypted_data: str):
        """Handle command progress update from agent."""
        try:
            decrypted = cipher.decrypt(encrypted_data)
            progress = json.loads(decrypted)
            
            command_id = progress.get("command_id")
            if command_id in pending_commands:
                pending_commands[command_id]["progress"].append(progress)
                
                # Broadcast to admin clients if any
                await self.sio.emit(
                    'command_progress',
                    {
                        "command_id": command_id,
                        "agent_id": progress.get("agent_id"),
                        "data": progress.get("data"),
                        "timestamp": progress.get("timestamp")
                    },
                    namespace='/'
                )
                
        except Exception as e:
            print(f"Progress error: {e}")
    
    async def on_result(self, sid: str, encrypted_data: str):
        """Handle command result from agent."""
        try:
            decrypted = cipher.decrypt(encrypted_data)
            result = json.loads(decrypted)
            
            command_id = result.get("command_id")
            agent_id = result.get("agent_id")
            
            # Store result
            if command_id in pending_commands:
                pending_commands[command_id]["result"] = result
                pending_commands[command_id]["completed_at"] = datetime.now().isoformat()
                pending_commands[command_id]["status"] = "completed"
            
            # Add to agent's command log
            if agent_id in connected_agents:
                connected_agents[agent_id]["command_logs"].append({
                    "command_id": command_id,
                    "result": result.get("data"),
                    "success": result.get("success"),
                    "timestamp": datetime.now().isoformat()
                })
            
            print(f"Command {command_id} completed for agent {agent_id}")
            
            # Broadcast to admin clients
            await self.sio.emit(
                'command_result',
                {
                    "command_id": command_id,
                    "agent_id": agent_id,
                    "success": result.get("success"),
                    "data": result.get("data"),
                    "timestamp": datetime.now().isoformat()
                },
                namespace='/'
            )
            
        except Exception as e:
            print(f"Result error: {e}")
    
    async def on_error(self, sid: str, encrypted_data: str):
        """Handle error from agent."""
        try:
            decrypted = cipher.decrypt(encrypted_data)
            error = json.loads(decrypted)
            
            command_id = error.get("command_id")
            
            if command_id in pending_commands:
                pending_commands[command_id]["status"] = "error"
                pending_commands[command_id]["error"] = error.get("error")
            
            print(f"Command error: {error}")
            
        except Exception as e:
            print(f"Error handler error: {e}")
    
    async def on_log(self, sid: str, encrypted_data: str):
        """Handle log message from agent."""
        try:
            decrypted = cipher.decrypt(encrypted_data)
            log = json.loads(decrypted)
            
            agent_id = log.get("agent_id")
            level = log.get("level", "info")
            message = log.get("message")
            
            print(f"[{agent_id}] [{level.upper()}] {message}")
            
        except Exception as e:
            print(f"Log error: {e}")


async def send_command_to_agent(agent_id: str, command: Dict[str, Any]):
    """
    Send a command to a specific agent.
    
    Args:
        agent_id: Target agent ID
        command: Command dictionary
    """
    global _sio_instance
    
    if agent_id not in connected_agents:
        print(f"Agent {agent_id} not found")
        return
    
    agent_info = connected_agents[agent_id]
    if not agent_info.get("online"):
        print(f"Agent {agent_id} is offline")
        return
    
    sid = agent_info.get("sid")
    if not sid:
        print(f"No SID for agent {agent_id}")
        return
    
    # Store pending command
    command_id = command.get("id")
    pending_commands[command_id] = {
        "command": command,
        "agent_id": agent_id,
        "status": "pending",
        "progress": [],
        "created_at": datetime.now().isoformat()
    }
    
    # Encrypt and send command
    try:
        if _sio_instance is None:
            print("Socket.IO instance not available")
            return
        
        encrypted = cipher.encrypt(json.dumps(command))
        await _sio_instance.emit('command', encrypted, to=sid, namespace='/agents')
        
        pending_commands[command_id]["status"] = "sent"
        print(f"Command {command_id} sent to agent {agent_id}")
        
    except Exception as e:
        pending_commands[command_id]["status"] = "error"
        pending_commands[command_id]["error"] = str(e)
        print(f"Failed to send command: {e}")


def get_agent_status(agent_id: str) -> Optional[Dict[str, Any]]:
    """Get current status of an agent."""
    if agent_id not in connected_agents:
        return None
    
    info = connected_agents[agent_id].copy()
    
    # Check if agent is still online (heartbeat timeout)
    if info.get("last_heartbeat"):
        last_hb = datetime.fromisoformat(info["last_heartbeat"])
        seconds_since = (datetime.now() - last_hb).total_seconds()
        if seconds_since > settings.HEARTBEAT_TIMEOUT:
            info["online"] = False
    
    return info
