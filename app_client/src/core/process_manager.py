"""
Autonova RMM - Process Manager
Functions for viewing and managing Windows processes.
"""

import psutil
import logging
from typing import Dict, Any, List, Callable

logger = logging.getLogger(__name__)


async def list_processes(progress_callback: Callable = None) -> Dict[str, Any]:
    """
    List all running processes with details.
    
    Returns:
        Dict with process list and stats
    """
    if progress_callback:
        await progress_callback({"message": "Recopilando lista de procesos...", "percent": 0})
    
    processes = []
    total_cpu = 0
    total_memory = 0
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                pinfo = proc.info
                processes.append({
                    "pid": pinfo['pid'],
                    "name": pinfo['name'],
                    "cpu": round(pinfo['cpu_percent'] or 0, 1),
                    "memory": round(pinfo['memory_percent'] or 0, 1),
                    "status": pinfo['status']
                })
                total_cpu += pinfo['cpu_percent'] or 0
                total_memory += pinfo['memory_percent'] or 0
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by memory usage
        processes.sort(key=lambda x: x['memory'], reverse=True)
        
        if progress_callback:
            await progress_callback({"message": f"Se encontraron {len(processes)} procesos", "percent": 100})
        
        return {
            "success": True,
            "total_processes": len(processes),
            "total_cpu": round(total_cpu, 1),
            "total_memory": round(total_memory, 1),
            "processes": processes[:50]  # Return top 50 by memory
        }
        
    except Exception as e:
        logger.error(f"Error listing processes: {e}")
        return {"success": False, "error": str(e)}


async def kill_process(pid: int, progress_callback: Callable = None) -> Dict[str, Any]:
    """
    Terminate a process by PID.
    
    Args:
        pid: Process ID to terminate
        progress_callback: Optional callback for progress updates
        
    Returns:
        Dict with result
    """
    try:
        if progress_callback:
            await progress_callback({"message": f"Terminando proceso {pid}...", "percent": 50})
        
        proc = psutil.Process(pid)
        name = proc.name()
        proc.terminate()
        
        # Wait for process to terminate
        proc.wait(timeout=5)
        
        if progress_callback:
            await progress_callback({"message": f"Proceso {name} terminado", "percent": 100})
        
        return {"success": True, "message": f"Proceso {name} (PID: {pid}) terminado"}
        
    except psutil.NoSuchProcess:
        return {"success": False, "error": f"Proceso {pid} no encontrado"}
    except psutil.AccessDenied:
        return {"success": False, "error": f"Acceso denegado para terminar proceso {pid}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
