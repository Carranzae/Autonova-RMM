"""
Autonova RMM - File Explorer and Security Scanner Module
Browse files, view downloads, recycle bin, browser history, and scan for threats.
"""

import os
import sys
import json
import sqlite3
import shutil
import winreg
import logging
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Callable, List, Optional

logger = logging.getLogger(__name__)


async def browse_files(path: str = None, progress_callback: Callable = None) -> Dict[str, Any]:
    """
    Browse files in a directory.
    Returns list of files and folders with metadata.
    """
    if path is None:
        path = os.path.expanduser("~")
    
    try:
        if progress_callback:
            await progress_callback({"message": f"📂 Explorando {path}...", "percent": 10})
        
        path = Path(path)
        if not path.exists():
            return {"success": False, "error": "Ruta no encontrada"}
        
        items = []
        
        # List directory contents
        try:
            for item in path.iterdir():
                try:
                    stat = item.stat()
                    items.append({
                        "name": item.name,
                        "path": str(item),
                        "is_dir": item.is_dir(),
                        "size": stat.st_size if item.is_file() else 0,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "extension": item.suffix.lower() if item.is_file() else ""
                    })
                except (PermissionError, OSError):
                    continue
        except PermissionError:
            return {"success": False, "error": "Acceso denegado a esta carpeta"}
        
        # Sort: folders first, then files
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        
        if progress_callback:
            await progress_callback({"message": f"✅ {len(items)} elementos encontrados", "percent": 100})
        
        return {
            "success": True,
            "path": str(path),
            "parent": str(path.parent) if path.parent != path else None,
            "items": items[:200],  # Limit to 200 items
            "total_count": len(items)
        }
    
    except Exception as e:
        logger.error(f"Error browsing files: {e}")
        return {"success": False, "error": str(e)}


async def view_downloads(progress_callback: Callable = None) -> Dict[str, Any]:
    """
    View files in the Downloads folder.
    """
    downloads_path = Path(os.path.expanduser("~")) / "Downloads"
    
    if progress_callback:
        await progress_callback({"message": "📥 Analizando carpeta de Descargas...", "percent": 20})
    
    if not downloads_path.exists():
        return {"success": False, "error": "Carpeta de descargas no encontrada"}
    
    files = []
    total_size = 0
    suspicious_extensions = ['.exe', '.msi', '.bat', '.cmd', '.vbs', '.js', '.scr', '.pif']
    
    try:
        for item in downloads_path.iterdir():
            if item.is_file():
                try:
                    stat = item.stat()
                    is_suspicious = item.suffix.lower() in suspicious_extensions
                    
                    files.append({
                        "name": item.name,
                        "path": str(item),
                        "size": stat.st_size,
                        "size_formatted": format_size(stat.st_size),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "extension": item.suffix.lower(),
                        "suspicious": is_suspicious
                    })
                    total_size += stat.st_size
                except (PermissionError, OSError):
                    continue
        
        # Sort by modification date (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)
        
        suspicious_count = sum(1 for f in files if f.get("suspicious"))
        
        if progress_callback:
            await progress_callback({
                "message": f"✅ {len(files)} archivos en Descargas ({format_size(total_size)})",
                "percent": 100
            })
        
        return {
            "success": True,
            "path": str(downloads_path),
            "files": files[:100],  # Limit
            "total_count": len(files),
            "total_size": format_size(total_size),
            "suspicious_count": suspicious_count
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


async def view_recycle_bin(progress_callback: Callable = None) -> Dict[str, Any]:
    """
    View contents of the Recycle Bin using PowerShell.
    """
    if progress_callback:
        await progress_callback({"message": "🗑️ Analizando Papelera de Reciclaje...", "percent": 20})
    
    try:
        # Use PowerShell to get recycle bin contents
        ps_command = '''
        $shell = New-Object -ComObject Shell.Application
        $recycleBin = $shell.NameSpace(0xa)
        $items = @()
        foreach($item in $recycleBin.Items()) {
            $items += @{
                Name = $item.Name
                Path = $item.Path
                Size = $item.Size
                DateDeleted = $item.ExtendedProperty("System.Recycle.DateDeleted")
                OriginalLocation = $item.ExtendedProperty("System.Recycle.DeletedFrom")
            }
        }
        $items | ConvertTo-Json
        '''
        
        result = subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_command],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout.strip():
            try:
                items = json.loads(result.stdout)
                if isinstance(items, dict):
                    items = [items]
                
                total_size = sum(item.get("Size", 0) or 0 for item in items)
                
                if progress_callback:
                    await progress_callback({
                        "message": f"✅ {len(items)} elementos en Papelera",
                        "percent": 100
                    })
                
                return {
                    "success": True,
                    "items": items[:100],
                    "total_count": len(items),
                    "total_size": format_size(total_size)
                }
            except json.JSONDecodeError:
                pass
        
        # Fallback: return empty
        if progress_callback:
            await progress_callback({"message": "✅ Papelera vacía o sin acceso", "percent": 100})
        
        return {"success": True, "items": [], "total_count": 0, "total_size": "0 B"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


async def scan_browser_history(progress_callback: Callable = None) -> Dict[str, Any]:
    """
    Scan browser history from Chrome, Firefox, Edge.
    """
    history = {
        "chrome": [],
        "firefox": [],
        "edge": [],
        "suspicious_sites": []
    }
    
    suspicious_patterns = [
        'torrent', 'crack', 'keygen', 'pirate', 'hack', 'warez',
        'download-free', 'free-software', 'serial-key'
    ]
    
    user_profile = Path(os.environ.get('LOCALAPPDATA', ''))
    
    # Chrome History
    if progress_callback:
        await progress_callback({"message": "🌐 Analizando Chrome...", "percent": 20})
    
    chrome_history = user_profile / 'Google' / 'Chrome' / 'User Data' / 'Default' / 'History'
    if chrome_history.exists():
        try:
            # Copy to temp to avoid lock
            temp_db = Path(os.environ.get('TEMP', '')) / 'chrome_history_temp.db'
            shutil.copy2(chrome_history, temp_db)
            
            conn = sqlite3.connect(str(temp_db))
            cursor = conn.cursor()
            cursor.execute('''
                SELECT url, title, visit_count, datetime(last_visit_time/1000000-11644473600, 'unixepoch') 
                FROM urls ORDER BY last_visit_time DESC LIMIT 50
            ''')
            
            for row in cursor.fetchall():
                entry = {"url": row[0], "title": row[1], "visits": row[2], "last_visit": row[3]}
                history["chrome"].append(entry)
                
                # Check for suspicious
                if any(p in row[0].lower() for p in suspicious_patterns):
                    history["suspicious_sites"].append({"browser": "Chrome", **entry})
            
            conn.close()
            temp_db.unlink()
        except Exception as e:
            logger.debug(f"Chrome history error: {e}")
    
    # Edge History
    if progress_callback:
        await progress_callback({"message": "🌐 Analizando Edge...", "percent": 50})
    
    edge_history = user_profile / 'Microsoft' / 'Edge' / 'User Data' / 'Default' / 'History'
    if edge_history.exists():
        try:
            temp_db = Path(os.environ.get('TEMP', '')) / 'edge_history_temp.db'
            shutil.copy2(edge_history, temp_db)
            
            conn = sqlite3.connect(str(temp_db))
            cursor = conn.cursor()
            cursor.execute('''
                SELECT url, title, visit_count, datetime(last_visit_time/1000000-11644473600, 'unixepoch') 
                FROM urls ORDER BY last_visit_time DESC LIMIT 50
            ''')
            
            for row in cursor.fetchall():
                entry = {"url": row[0], "title": row[1], "visits": row[2], "last_visit": row[3]}
                history["edge"].append(entry)
                
                if any(p in row[0].lower() for p in suspicious_patterns):
                    history["suspicious_sites"].append({"browser": "Edge", **entry})
            
            conn.close()
            temp_db.unlink()
        except Exception as e:
            logger.debug(f"Edge history error: {e}")
    
    if progress_callback:
        await progress_callback({
            "message": f"✅ Historial analizado. {len(history['suspicious_sites'])} sitios sospechosos",
            "percent": 100
        })
    
    return {
        "success": True,
        "browsers_found": [b for b in ["chrome", "edge", "firefox"] if history[b]],
        "total_entries": len(history["chrome"]) + len(history["edge"]) + len(history["firefox"]),
        "suspicious_count": len(history["suspicious_sites"]),
        "history": history
    }


async def scan_threats(progress_callback: Callable = None) -> Dict[str, Any]:
    """
    Scan for potential threats: suspicious files, processes, startup items.
    """
    threats = []
    
    # Phase 1: Check suspicious startup programs
    if progress_callback:
        await progress_callback({"message": "🛡️ Escaneando programas de inicio...", "percent": 10})
    
    startup_threats = await scan_startup_threats()
    threats.extend(startup_threats)
    
    # Phase 2: Check for suspicious processes
    if progress_callback:
        await progress_callback({"message": "🔍 Analizando procesos sospechosos...", "percent": 30})
    
    import psutil
    suspicious_process_names = [
        'cryptominer', 'miner', 'xmrig', 'ccminer', 'cgminer',
        'keylogger', 'trojan', 'backdoor', 'rat.exe', 'malware'
    ]
    
    for proc in psutil.process_iter(['name', 'exe', 'username']):
        try:
            name = proc.info['name'].lower()
            if any(s in name for s in suspicious_process_names):
                threats.append({
                    "type": "process",
                    "severity": "high",
                    "name": proc.info['name'],
                    "path": proc.info['exe'],
                    "description": "Proceso potencialmente malicioso"
                })
        except:
            continue
    
    # Phase 3: Check for suspicious files in common locations
    if progress_callback:
        await progress_callback({"message": "📁 Escaneando archivos sospechosos...", "percent": 60})
    
    suspicious_locations = [
        Path(os.environ.get('TEMP', '')),
        Path(os.environ.get('APPDATA', '')) / 'Local' / 'Temp',
        Path(os.path.expanduser("~")) / 'Downloads'
    ]
    
    suspicious_names = ['crack', 'keygen', 'patch', 'activator', 'loader']
    
    for location in suspicious_locations:
        if location.exists():
            try:
                for file in location.iterdir():
                    if file.is_file():
                        name_lower = file.name.lower()
                        if any(s in name_lower for s in suspicious_names):
                            threats.append({
                                "type": "file",
                                "severity": "medium",
                                "name": file.name,
                                "path": str(file),
                                "description": "Archivo potencialmente peligroso"
                            })
            except:
                continue
    
    # Phase 4: Check Windows Defender status
    if progress_callback:
        await progress_callback({"message": "🛡️ Verificando Windows Defender...", "percent": 80})
    
    try:
        result = subprocess.run(
            ['powershell', '-Command', 'Get-MpComputerStatus | Select-Object AntivirusEnabled, RealTimeProtectionEnabled | ConvertTo-Json'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            status = json.loads(result.stdout)
            if not status.get('AntivirusEnabled') or not status.get('RealTimeProtectionEnabled'):
                threats.append({
                    "type": "security",
                    "severity": "critical",
                    "name": "Windows Defender Desactivado",
                    "description": "La protección en tiempo real está desactivada"
                })
    except:
        pass
    
    if progress_callback:
        await progress_callback({
            "message": f"✅ Escaneo completado. {len(threats)} amenazas encontradas",
            "percent": 100
        })
    
    return {
        "success": True,
        "threats": threats,
        "threat_count": len(threats),
        "critical_count": sum(1 for t in threats if t.get("severity") == "critical"),
        "high_count": sum(1 for t in threats if t.get("severity") == "high"),
        "medium_count": sum(1 for t in threats if t.get("severity") == "medium")
    }


async def scan_startup_threats() -> List[Dict]:
    """Scan startup items for suspicious entries."""
    threats = []
    suspicious_keywords = ['temp', 'appdata', 'update', 'helper', 'service', 'runtime']
    
    startup_locations = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ]
    
    for root, path in startup_locations:
        try:
            key = winreg.OpenKey(root, path)
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    
                    # Check if path is suspicious
                    value_lower = value.lower()
                    if any(k in value_lower for k in suspicious_keywords):
                        threats.append({
                            "type": "startup",
                            "severity": "medium",
                            "name": name,
                            "path": value,
                            "description": "Programa de inicio sospechoso"
                        })
                    
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except:
            continue
    
    return threats


async def scan_network(progress_callback: Callable = None) -> Dict[str, Any]:
    """
    Scan network for open ports and suspicious connections.
    """
    if progress_callback:
        await progress_callback({"message": "🌐 Escaneando conexiones de red...", "percent": 20})
    
    import psutil
    
    connections = []
    suspicious_ports = [4444, 5555, 6666, 7777, 8888, 31337, 12345]  # Common malware ports
    suspicious_connections = []
    
    for conn in psutil.net_connections(kind='inet'):
        try:
            local_addr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A"
            remote_addr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A"
            
            entry = {
                "local": local_addr,
                "remote": remote_addr,
                "status": conn.status,
                "pid": conn.pid
            }
            
            try:
                if conn.pid:
                    proc = psutil.Process(conn.pid)
                    entry["process"] = proc.name()
            except:
                entry["process"] = "Unknown"
            
            connections.append(entry)
            
            # Check for suspicious ports
            if conn.laddr and conn.laddr.port in suspicious_ports:
                suspicious_connections.append({**entry, "reason": "Puerto sospechoso"})
            if conn.raddr and conn.raddr.port in suspicious_ports:
                suspicious_connections.append({**entry, "reason": "Conexión a puerto sospechoso"})
                
        except:
            continue
    
    if progress_callback:
        await progress_callback({
            "message": f"✅ {len(connections)} conexiones analizadas",
            "percent": 100
        })
    
    return {
        "success": True,
        "total_connections": len(connections),
        "connections": connections[:50],  # Limit
        "suspicious_count": len(suspicious_connections),
        "suspicious_connections": suspicious_connections
    }


async def delete_file(file_path: str, progress_callback: Callable = None) -> Dict[str, Any]:
    """
    Delete a specific file.
    """
    try:
        path = Path(file_path)
        
        if not path.exists():
            return {"success": False, "error": "Archivo no encontrado"}
        
        if progress_callback:
            await progress_callback({"message": f"🗑️ Eliminando {path.name}...", "percent": 50})
        
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        
        if progress_callback:
            await progress_callback({"message": f"✅ {path.name} eliminado", "percent": 100})
        
        return {"success": True, "deleted": str(path)}
    
    except PermissionError:
        return {"success": False, "error": "Permiso denegado"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"
