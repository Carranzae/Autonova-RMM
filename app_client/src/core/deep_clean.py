"""
Autonova RMM - Deep Clean Module
Performs aggressive system cleanup: temp files, registry, caches.
Uses subprocess.Popen for safe command execution (never os.system).
"""

import asyncio
import os
import shutil
import subprocess
import tempfile
import winreg
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class DeepCleaner:
    """Performs deep system cleaning operations."""
    
    # Directories to clean
    TEMP_DIRS = [
        os.environ.get('TEMP', ''),
        os.environ.get('TMP', ''),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp'),
        os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Temp'),
        os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Prefetch'),
    ]
    
    # Windows Update cache
    UPDATE_CACHE = os.path.join(
        os.environ.get('WINDIR', 'C:\\Windows'),
        'SoftwareDistribution', 'Download'
    )
    
    # Browser caches
    BROWSER_CACHES = {
        "chrome": os.path.join(
            os.environ.get('LOCALAPPDATA', ''),
            'Google', 'Chrome', 'User Data', 'Default', 'Cache'
        ),
        "edge": os.path.join(
            os.environ.get('LOCALAPPDATA', ''),
            'Microsoft', 'Edge', 'User Data', 'Default', 'Cache'
        ),
        "firefox": os.path.join(
            os.environ.get('LOCALAPPDATA', ''),
            'Mozilla', 'Firefox', 'Profiles'
        )
    }
    
    # Registry locations to clean
    REGISTRY_CLEANUP = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\TypedPaths"),
    ]
    
    def __init__(self, callback: Optional[callable] = None):
        """
        Initialize the deep cleaner.
        
        Args:
            callback: Optional async function for progress updates
        """
        self.callback = callback
        self.stats = {
            "files_deleted": 0,
            "bytes_freed": 0,
            "errors": []
        }
    
    async def _report(self, message: str, progress: int = 0):
        """Send progress update to callback."""
        if self.callback:
            await self.callback({
                "type": "progress",
                "module": "deep_clean",
                "message": message,
                "progress": progress,
                "timestamp": datetime.now().isoformat()
            })
    
    def _safe_delete_file(self, filepath: str) -> bool:
        """
        Safely delete a single file.
        
        Args:
            filepath: Path to file to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            file_size = os.path.getsize(filepath)
            os.remove(filepath)
            self.stats["files_deleted"] += 1
            self.stats["bytes_freed"] += file_size
            return True
        except PermissionError:
            # File is in use, try force delete
            return self._force_delete(filepath)
        except Exception as e:
            self.stats["errors"].append(f"Delete failed: {filepath} - {str(e)}")
            return False
    
    def _force_delete(self, filepath: str) -> bool:
        """
        Force delete a locked file using Windows command.
        Uses subprocess.Popen for safe execution.
        """
        try:
            # Use del /f /q for force delete
            process = subprocess.Popen(
                ['cmd', '/c', 'del', '/f', '/q', filepath],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            process.wait(timeout=10)
            
            if not os.path.exists(filepath):
                self.stats["files_deleted"] += 1
                return True
            return False
        except Exception:
            return False
    
    def _safe_delete_dir(self, dirpath: str) -> int:
        """
        Recursively delete directory contents.
        
        Args:
            dirpath: Path to directory
            
        Returns:
            Number of files deleted
        """
        deleted = 0
        if not os.path.exists(dirpath):
            return 0
        
        try:
            for root, dirs, files in os.walk(dirpath, topdown=False):
                for name in files:
                    filepath = os.path.join(root, name)
                    if self._safe_delete_file(filepath):
                        deleted += 1
                
                for name in dirs:
                    try:
                        os.rmdir(os.path.join(root, name))
                    except Exception:
                        pass
        except Exception as e:
            self.stats["errors"].append(f"Dir walk failed: {dirpath} - {str(e)}")
        
        return deleted
    
    async def clean_temp_files(self) -> Dict[str, int]:
        """Clean temporary file directories."""
        await self._report("Cleaning temporary files...", 10)
        
        results = {}
        for temp_dir in self.TEMP_DIRS:
            if temp_dir and os.path.exists(temp_dir):
                await self._report(f"Cleaning: {temp_dir}", 15)
                deleted = self._safe_delete_dir(temp_dir)
                results[temp_dir] = deleted
        
        return results
    
    async def clean_windows_update_cache(self) -> Dict[str, Any]:
        """Clean Windows Update download cache."""
        await self._report("Cleaning Windows Update cache...", 30)
        
        result = {"path": self.UPDATE_CACHE, "deleted": 0, "stopped_service": False}
        
        # Stop Windows Update service first
        try:
            process = subprocess.Popen(
                ['net', 'stop', 'wuauserv'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            process.wait(timeout=30)
            result["stopped_service"] = True
        except Exception:
            pass
        
        # Clean the cache
        if os.path.exists(self.UPDATE_CACHE):
            result["deleted"] = self._safe_delete_dir(self.UPDATE_CACHE)
        
        # Restart Windows Update service
        try:
            subprocess.Popen(
                ['net', 'start', 'wuauserv'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception:
            pass
        
        return result
    
    async def clean_browser_caches(self) -> Dict[str, int]:
        """Clean browser cache directories."""
        await self._report("Cleaning browser caches...", 45)
        
        results = {}
        for browser, cache_path in self.BROWSER_CACHES.items():
            if os.path.exists(cache_path):
                await self._report(f"Cleaning {browser} cache...", 50)
                
                if browser == "firefox":
                    # Firefox has profile subdirectories
                    try:
                        for profile in os.listdir(cache_path):
                            profile_cache = os.path.join(cache_path, profile, 'cache2')
                            if os.path.exists(profile_cache):
                                results[f"{browser}_{profile}"] = self._safe_delete_dir(profile_cache)
                    except Exception:
                        pass
                else:
                    results[browser] = self._safe_delete_dir(cache_path)
        
        return results
    
    async def clean_prefetch(self) -> int:
        """Clean Windows Prefetch folder."""
        await self._report("Cleaning Prefetch folder...", 60)
        
        prefetch_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Prefetch')
        if os.path.exists(prefetch_dir):
            return self._safe_delete_dir(prefetch_dir)
        return 0
    
    async def clean_recycle_bin(self) -> bool:
        """Empty the Recycle Bin."""
        await self._report("Emptying Recycle Bin...", 70)
        
        try:
            # PowerShell command to empty recycle bin
            process = subprocess.Popen(
                ['powershell', '-Command', 'Clear-RecycleBin -Force -ErrorAction SilentlyContinue'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            process.wait(timeout=60)
            return True
        except Exception as e:
            self.stats["errors"].append(f"Recycle bin cleanup failed: {str(e)}")
            return False
    
    async def clean_registry_mru(self) -> Dict[str, Any]:
        """Clean MRU (Most Recently Used) lists from registry."""
        await self._report("Cleaning registry MRU entries...", 80)
        
        results = {"cleaned": 0, "failed": 0}
        
        for hkey, subkey in self.REGISTRY_CLEANUP:
            try:
                key = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_ALL_ACCESS)
                
                # Get number of values
                info = winreg.QueryInfoKey(key)
                num_values = info[1]
                
                # Delete all values except default
                values_to_delete = []
                for i in range(num_values):
                    try:
                        value_name = winreg.EnumValue(key, i)[0]
                        if value_name and value_name != "MRUList":
                            values_to_delete.append(value_name)
                    except Exception:
                        break
                
                for value_name in values_to_delete:
                    try:
                        winreg.DeleteValue(key, value_name)
                        results["cleaned"] += 1
                    except Exception:
                        results["failed"] += 1
                
                winreg.CloseKey(key)
            except Exception:
                continue
        
        return results
    
    async def run_disk_cleanup(self) -> Dict[str, Any]:
        """Run Windows Disk Cleanup utility with all options."""
        await self._report("Running Windows Disk Cleanup...", 90)
        
        result = {"success": False, "output": ""}
        
        try:
            # Run cleanmgr with sageset to configure and run
            # Use preset configuration 1
            process = subprocess.Popen(
                ['cleanmgr', '/d', 'C:', '/verylowdisk'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            stdout, stderr = process.communicate(timeout=300)
            result["success"] = process.returncode == 0
            result["output"] = stdout.decode('utf-8', errors='ignore')
        except subprocess.TimeoutExpired:
            result["output"] = "Disk Cleanup timed out"
        except Exception as e:
            result["output"] = str(e)
        
        return result
    
    async def run_full_clean(self) -> Dict[str, Any]:
        """
        Execute complete deep cleaning routine.
        
        Returns:
            Complete cleanup report
        """
        await self._report("Starting deep clean...", 0)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "temp_files": await self.clean_temp_files(),
            "update_cache": await self.clean_windows_update_cache(),
            "browser_caches": await self.clean_browser_caches(),
            "prefetch": await self.clean_prefetch(),
            "recycle_bin": await self.clean_recycle_bin(),
            "registry_mru": await self.clean_registry_mru(),
            "stats": {
                "total_files_deleted": self.stats["files_deleted"],
                "total_bytes_freed": self.stats["bytes_freed"],
                "bytes_freed_mb": round(self.stats["bytes_freed"] / (1024 * 1024), 2),
                "errors_count": len(self.stats["errors"]),
                "errors": self.stats["errors"][:10]  # Limit error list
            }
        }
        
        await self._report(
            f"Deep clean complete! Freed {report['stats']['bytes_freed_mb']} MB",
            100
        )
        
        return report


async def run_deep_clean(callback: Optional[callable] = None) -> Dict[str, Any]:
    """
    Convenience function to run full deep clean.
    
    Args:
        callback: Optional async function for progress updates
        
    Returns:
        Complete cleanup report
    """
    cleaner = DeepCleaner(callback)
    return await cleaner.run_full_clean()
