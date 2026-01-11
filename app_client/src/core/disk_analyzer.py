"""
Autonova RMM - Disk Analyzer (Optimized)
Fast disk usage analysis without deep recursive scanning.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Callable, List
import psutil
import asyncio

logger = logging.getLogger(__name__)


def format_size(bytes_size: int) -> str:
    """Format bytes to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"


def get_folder_size_fast(path: Path, max_depth: int = 1) -> int:
    """
    Calculate folder size quickly by limiting depth.
    Only scans 1-2 levels deep for speed.
    """
    total = 0
    try:
        # Only iterate immediate children, not recursive
        for entry in path.iterdir():
            try:
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir() and max_depth > 0:
                    # Only go 1 level deep for subdirectories
                    for sub_entry in entry.iterdir():
                        try:
                            if sub_entry.is_file():
                                total += sub_entry.stat().st_size
                        except (PermissionError, OSError):
                            continue
            except (PermissionError, OSError):
                continue
    except (PermissionError, OSError):
        pass
    return total


async def analyze_disk(progress_callback: Callable = None) -> Dict[str, Any]:
    """
    Analyze disk usage quickly.
    Optimized for speed - shows results in seconds not minutes.
    """
    results = {
        "partitions": [],
        "junk_analysis": [],
        "total_junk_size": 0,
        "total_junk_bytes": 0
    }
    
    try:
        # Phase 1: Get partition info (fast)
        if progress_callback:
            await progress_callback({"message": "📊 Obteniendo información de particiones...", "percent": 10})
        
        await asyncio.sleep(0.1)  # Allow UI update
        
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                results["partitions"].append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "total": format_size(usage.total),
                    "used": format_size(usage.used),
                    "free": format_size(usage.free),
                    "percent": usage.percent
                })
                
                if progress_callback:
                    await progress_callback({
                        "message": f"  💿 {partition.mountpoint} - {usage.percent}% usado ({format_size(usage.free)} libre)",
                        "percent": 20
                    })
            except (PermissionError, OSError):
                continue
        
        # Phase 2: Check common junk locations (quick estimation)
        if progress_callback:
            await progress_callback({"message": "🔍 Analizando archivos temporales...", "percent": 30})
        
        await asyncio.sleep(0.1)
        
        junk_locations = [
            (Path(os.environ.get('TEMP', 'C:\\Windows\\Temp')), "Temp Usuario"),
            (Path(os.environ.get('WINDIR', 'C:\\Windows')) / 'Temp', "Temp Sistema"),
            (Path(os.environ.get('WINDIR', 'C:\\Windows')) / 'Prefetch', "Prefetch"),
            (Path(os.environ.get('LOCALAPPDATA', '')) / 'Temp', "LocalAppData Temp"),
        ]
        
        total_junk = 0
        for i, (path, name) in enumerate(junk_locations):
            if path.exists():
                # Count files quickly (just top level)
                try:
                    file_count = sum(1 for _ in path.iterdir() if _.is_file())
                    size = get_folder_size_fast(path, max_depth=1)
                    total_junk += size
                    
                    results["junk_analysis"].append({
                        "path": str(path),
                        "name": name,
                        "size": format_size(size),
                        "size_bytes": size,
                        "files": file_count
                    })
                    
                    if progress_callback:
                        percent = 30 + int((i + 1) / len(junk_locations) * 40)
                        await progress_callback({
                            "message": f"  📁 {name}: {format_size(size)} ({file_count} archivos)",
                            "percent": percent
                        })
                except (PermissionError, OSError):
                    continue
            
            await asyncio.sleep(0.05)  # Small delay for UI updates
        
        results["total_junk_size"] = format_size(total_junk)
        results["total_junk_bytes"] = total_junk
        
        # Phase 3: Browser cache estimation
        if progress_callback:
            await progress_callback({"message": "🌐 Analizando caché de navegadores...", "percent": 75})
        
        await asyncio.sleep(0.1)
        
        browser_caches = [
            (Path(os.environ.get('LOCALAPPDATA', '')) / 'Google' / 'Chrome' / 'User Data' / 'Default' / 'Cache', "Chrome"),
            (Path(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft' / 'Edge' / 'User Data' / 'Default' / 'Cache', "Edge"),
            (Path(os.environ.get('APPDATA', '')) / 'Mozilla' / 'Firefox' / 'Profiles', "Firefox"),
        ]
        
        browser_total = 0
        for path, name in browser_caches:
            if path.exists():
                try:
                    size = get_folder_size_fast(path, max_depth=0)
                    browser_total += size
                    results["junk_analysis"].append({
                        "path": str(path),
                        "name": f"Caché {name}",
                        "size": format_size(size),
                        "size_bytes": size
                    })
                    
                    if progress_callback:
                        await progress_callback({
                            "message": f"  🌐 {name}: {format_size(size)}",
                            "percent": 85
                        })
                except:
                    continue
        
        results["total_junk_bytes"] += browser_total
        results["total_junk_size"] = format_size(results["total_junk_bytes"])
        
        # Final summary
        if progress_callback:
            await progress_callback({
                "message": f"📊 Resumen: {len(results['partitions'])} particiones, {results['total_junk_size']} de basura",
                "percent": 100,
                "level": "success"
            })
        
        results["success"] = True
        return results
        
    except Exception as e:
        logger.error(f"Error analyzing disk: {e}")
        if progress_callback:
            await progress_callback({"message": f"❌ Error: {str(e)}", "level": "error"})
        return {"success": False, "error": str(e)}


async def get_disk_usage(progress_callback: Callable = None) -> Dict[str, Any]:
    """Get simple disk usage summary."""
    try:
        partitions = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                partitions.append({
                    "drive": partition.mountpoint,
                    "total_gb": round(usage.total / (1024**3), 1),
                    "free_gb": round(usage.free / (1024**3), 1),
                    "percent": usage.percent
                })
            except:
                continue
        
        return {"success": True, "partitions": partitions}
    except Exception as e:
        return {"success": False, "error": str(e)}
