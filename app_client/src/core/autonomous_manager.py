"""
Autonova RMM - Autonomous Mode Manager
Intelligent system that operates independently when disconnected.
Queues actions and decisions for sync when connection is restored.
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent connection states."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    AUTONOMOUS = "autonomous"


class ActionPriority(Enum):
    """Priority levels for queued actions."""
    CRITICAL = 1  # Security threats
    HIGH = 2      # System repairs
    MEDIUM = 3    # Optimizations
    LOW = 4       # Maintenance


class AutonomousManager:
    """
    Manages autonomous operation when disconnected from server.
    
    Features:
    - Queues actions when offline
    - Makes intelligent decisions based on scan results
    - Retries connection with exponential backoff
    - Syncs queued data when connection is restored
    """
    
    def __init__(self, progress_callback: Callable = None):
        self.state = AgentState.DISCONNECTED
        self.progress_callback = progress_callback
        
        # Action queue for offline mode
        self.action_queue: List[Dict[str, Any]] = []
        self.completed_actions: List[Dict[str, Any]] = []
        self.pending_sync: List[Dict[str, Any]] = []
        
        # Decision engine state
        self.last_scan_results: Dict[str, Any] = {}
        self.recommendations: List[Dict[str, Any]] = []
        
        # Connection retry settings
        self.retry_interval = 5  # Start with 5 seconds
        self.max_retry_interval = 600  # Max 10 minutes
        self.retry_count = 0
        
        # Persistence
        self.data_dir = Path(os.environ.get('LOCALAPPDATA', '')) / 'Autonova'
        self.queue_file = self.data_dir / 'action_queue.json'
        self.sync_file = self.data_dir / 'pending_sync.json'
        
        # Load persisted data
        self._load_persisted_data()
    
    async def log(self, message: str, level: str = "info"):
        """Log message and send to callback if available."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[AUTONOMOUS] [{timestamp}] {message}")
        
        if self.progress_callback:
            try:
                await self.progress_callback({
                    "message": f"[AUTÓNOMO] {message}",
                    "timestamp": timestamp,
                    "level": level
                })
            except:
                pass  # Ignore if callback fails (disconnected)
    
    def _load_persisted_data(self):
        """Load queued actions from disk."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            if self.queue_file.exists():
                with open(self.queue_file, 'r') as f:
                    self.action_queue = json.load(f)
                    
            if self.sync_file.exists():
                with open(self.sync_file, 'r') as f:
                    self.pending_sync = json.load(f)
        except Exception as e:
            logger.error(f"Error loading persisted data: {e}")
    
    def _save_persisted_data(self):
        """Save queued actions to disk."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            with open(self.queue_file, 'w') as f:
                json.dump(self.action_queue, f, indent=2)
                
            with open(self.sync_file, 'w') as f:
                json.dump(self.pending_sync, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving persisted data: {e}")
    
    def queue_action(self, action_type: str, params: Dict[str, Any] = None, 
                     priority: ActionPriority = ActionPriority.MEDIUM):
        """Add action to offline queue."""
        action = {
            "id": f"action_{datetime.now().timestamp()}",
            "type": action_type,
            "params": params or {},
            "priority": priority.value,
            "queued_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        self.action_queue.append(action)
        # Sort by priority
        self.action_queue.sort(key=lambda x: x["priority"])
        self._save_persisted_data()
        
        return action["id"]
    
    def queue_for_sync(self, data_type: str, data: Dict[str, Any]):
        """Queue data to sync when connection is restored."""
        sync_item = {
            "type": data_type,
            "data": data,
            "queued_at": datetime.now().isoformat()
        }
        self.pending_sync.append(sync_item)
        self._save_persisted_data()
    
    async def analyze_and_decide(self, scan_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze scan results and make autonomous decisions.
        Returns list of recommended actions.
        """
        self.last_scan_results = scan_results
        self.recommendations = []
        
        await self.log("Analizando resultados del escaneo...")
        
        # Analyze health score
        score = scan_results.get("score", 100)
        
        if score < 40:
            await self.log("⚠️ Sistema en estado CRÍTICO", "danger")
            self.recommendations.append({
                "action": "full_repair",
                "priority": ActionPriority.CRITICAL,
                "reason": f"Puntuación de salud muy baja: {score}/100"
            })
        elif score < 60:
            await self.log("⚠️ Sistema necesita atención", "warning")
            self.recommendations.append({
                "action": "deep_clean",
                "priority": ActionPriority.HIGH,
                "reason": f"Puntuación de salud baja: {score}/100"
            })
        
        # Check for threats
        threats = scan_results.get("threats_found", [])
        if threats:
            await self.log(f"🚨 {len(threats)} amenazas detectadas", "danger")
            
            for threat in threats:
                threat_type = threat.get("type", "unknown")
                
                if threat_type == "suspicious_process":
                    self.recommendations.append({
                        "action": "kill_process",
                        "priority": ActionPriority.CRITICAL,
                        "params": {"pid": threat.get("pid"), "name": threat.get("name")},
                        "reason": f"Proceso sospechoso: {threat.get('name')}"
                    })
                elif threat_type == "suspicious_connection":
                    self.recommendations.append({
                        "action": "block_connection",
                        "priority": ActionPriority.CRITICAL,
                        "params": {"port": threat.get("port")},
                        "reason": f"Conexión sospechosa en puerto {threat.get('port')}"
                    })
        
        # Check for issues
        issues = scan_results.get("issues_found", [])
        for issue in issues:
            severity = issue.get("severity", "medium")
            issue_type = issue.get("type", "unknown")
            
            if issue_type == "disk" and severity == "high":
                self.recommendations.append({
                    "action": "clean_disk",
                    "priority": ActionPriority.HIGH,
                    "reason": issue.get("message", "Disco casi lleno")
                })
            elif issue_type == "memory" and severity == "high":
                self.recommendations.append({
                    "action": "free_memory",
                    "priority": ActionPriority.HIGH,
                    "reason": issue.get("message", "Memoria casi llena")
                })
            elif issue_type == "security":
                self.recommendations.append({
                    "action": "fix_security",
                    "priority": ActionPriority.CRITICAL,
                    "reason": issue.get("message", "Problema de seguridad")
                })
        
        # Log recommendations
        if self.recommendations:
            await self.log(f"📋 {len(self.recommendations)} acciones recomendadas")
            for rec in self.recommendations[:5]:
                await self.log(f"   → {rec['action']}: {rec['reason']}")
        else:
            await self.log("✅ No se requieren acciones inmediatas", "success")
        
        return self.recommendations
    
    async def execute_autonomous_actions(self, executor) -> Dict[str, Any]:
        """
        Execute queued actions autonomously.
        
        Args:
            executor: CommandExecutor instance
            
        Returns:
            Summary of executed actions
        """
        self.state = AgentState.AUTONOMOUS
        await self.log("🤖 Iniciando modo autónomo...")
        
        executed = []
        failed = []
        
        # Execute high-priority actions first
        priority_actions = [a for a in self.action_queue if a["status"] == "pending"]
        
        for action in priority_actions:
            try:
                await self.log(f"Ejecutando: {action['type']}...")
                
                # Create mock command
                command = {
                    "id": action["id"],
                    "type": action["type"],
                    "params": action.get("params", {})
                }
                
                result = await executor.execute(command)
                
                action["status"] = "completed"
                action["result"] = result
                action["completed_at"] = datetime.now().isoformat()
                
                self.completed_actions.append(action)
                executed.append(action)
                
                await self.log(f"✓ {action['type']} completado", "success")
                
            except Exception as e:
                action["status"] = "failed"
                action["error"] = str(e)
                failed.append(action)
                await self.log(f"✗ Error en {action['type']}: {e}", "error")
        
        # Clean up completed actions from queue
        self.action_queue = [a for a in self.action_queue if a["status"] == "pending"]
        self._save_persisted_data()
        
        # Queue results for sync
        summary = {
            "executed_at": datetime.now().isoformat(),
            "executed_count": len(executed),
            "failed_count": len(failed),
            "actions": executed + failed
        }
        
        self.queue_for_sync("autonomous_results", summary)
        
        await self.log(f"Modo autónomo: {len(executed)} exitosos, {len(failed)} fallidos")
        
        return summary
    
    def get_retry_interval(self) -> int:
        """Calculate next retry interval with exponential backoff."""
        interval = min(
            self.retry_interval * (2 ** self.retry_count),
            self.max_retry_interval
        )
        return interval
    
    async def connection_lost(self):
        """Handle connection loss."""
        self.state = AgentState.DISCONNECTED
        self.retry_count = 0
        await self.log("Conexión perdida. Entrando en modo autónomo...")
    
    async def connection_restored(self, socket_manager):
        """Handle connection restoration - sync pending data."""
        self.state = AgentState.CONNECTED
        self.retry_count = 0
        
        await self.log("✅ Conexión restaurada. Sincronizando datos...")
        
        # Sync pending data
        for item in self.pending_sync:
            try:
                await socket_manager.send_log(
                    "info",
                    f"Sync: {item['type']} - {json.dumps(item['data'])[:200]}"
                )
            except Exception as e:
                logger.error(f"Sync error: {e}")
        
        # Clear synced data
        synced_count = len(self.pending_sync)
        self.pending_sync = []
        self._save_persisted_data()
        
        await self.log(f"Sincronizados {synced_count} elementos pendientes")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current autonomous manager status."""
        return {
            "state": self.state.value,
            "queued_actions": len(self.action_queue),
            "pending_sync": len(self.pending_sync),
            "completed_actions": len(self.completed_actions),
            "recommendations": len(self.recommendations),
            "last_scan_score": self.last_scan_results.get("score", None)
        }


# Global instance
_autonomous_manager: Optional[AutonomousManager] = None


def get_autonomous_manager(progress_callback: Callable = None) -> AutonomousManager:
    """Get or create the global autonomous manager instance."""
    global _autonomous_manager
    if _autonomous_manager is None:
        _autonomous_manager = AutonomousManager(progress_callback)
    else:
        _autonomous_manager.progress_callback = progress_callback
    return _autonomous_manager
