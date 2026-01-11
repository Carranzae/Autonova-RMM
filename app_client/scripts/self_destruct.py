"""
Autonova RMM - Self-Destruct Module
Generates a script for complete agent removal without leaving traces.
"""

import os
import sys
import subprocess
import tempfile
import asyncio
from datetime import datetime
from typing import Optional
import winreg


async def initiate_self_destruct(delay_seconds: int = 5) -> dict:
    """
    Initiate the self-destruction sequence.
    
    Generates a batch script that:
    1. Waits for the agent process to exit
    2. Deletes all agent files
    3. Removes registry entries
    4. Cleans up scheduled tasks
    5. Deletes itself
    
    Args:
        delay_seconds: Seconds to wait before deletion
        
    Returns:
        Status dictionary
    """
    result = {
        "success": False,
        "script_path": None,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # Get agent paths
        if getattr(sys, 'frozen', False):
            agent_path = sys.executable
            agent_dir = os.path.dirname(agent_path)
        else:
            agent_path = os.path.abspath(sys.argv[0])
            agent_dir = os.path.dirname(agent_path)
        
        # Generate the self-destruct batch script
        script_content = generate_cleanup_script(
            agent_path=agent_path,
            agent_dir=agent_dir,
            delay_seconds=delay_seconds
        )
        
        # Write script to temp directory
        script_path = os.path.join(tempfile.gettempdir(), f"cleanup_{os.getpid()}.bat")
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        result["script_path"] = script_path
        
        # Remove from registry autostart
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.DeleteValue(key, "AutonovaAgent")
            winreg.CloseKey(key)
        except Exception:
            pass  # May not exist
        
        # Launch the cleanup script
        subprocess.Popen(
            ['cmd', '/c', 'start', '/min', '', script_path],
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            close_fds=True
        )
        
        result["success"] = True
        
        # Schedule process exit
        asyncio.get_event_loop().call_later(2, lambda: os._exit(0))
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def generate_cleanup_script(
    agent_path: str,
    agent_dir: str,
    delay_seconds: int = 5
) -> str:
    """
    Generate the batch script content for cleanup.
    
    Args:
        agent_path: Full path to agent executable
        agent_dir: Directory containing agent files
        delay_seconds: Delay before cleanup starts
        
    Returns:
        Batch script content as string
    """
    # Get the script's own path for self-deletion
    script_name = f"cleanup_{os.getpid()}.bat"
    script_path = os.path.join(tempfile.gettempdir(), script_name)
    
    script = f'''@echo off
:: Autonova RMM - Self-Destruct Script
:: Generated: {datetime.now().isoformat()}
:: This script removes all traces of the agent

:: Hide the window
if not "%1"=="am_admin" (
    powershell -Command "Start-Process -FilePath '%~0' -ArgumentList 'am_admin' -WindowStyle Hidden"
    exit /b
)

:: Wait for main process to exit
echo Waiting for agent to terminate...
:waitloop
timeout /t 1 /nobreak >nul
tasklist /fi "pid eq {os.getpid()}" 2>nul | find "{os.getpid()}" >nul
if not errorlevel 1 goto waitloop

:: Additional delay for safety
timeout /t {delay_seconds} /nobreak >nul

echo Starting cleanup...

:: Kill any remaining agent processes
taskkill /f /im "autonova_agent.exe" 2>nul
taskkill /f /im "python.exe" /fi "WINDOWTITLE eq Autonova*" 2>nul

:: Remove agent directory
echo Removing agent files...
rd /s /q "{agent_dir}" 2>nul

:: If exe is outside agent dir, delete it separately
if exist "{agent_path}" (
    del /f /q "{agent_path}" 2>nul
)

:: Clean registry entries
echo Cleaning registry...
reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "AutonovaAgent" /f 2>nul
reg delete "HKCU\\Software\\Autonova" /f 2>nul
reg delete "HKLM\\Software\\Autonova" /f 2>nul

:: Remove scheduled tasks
echo Removing scheduled tasks...
schtasks /delete /tn "AutonovaHeartbeat" /f 2>nul
schtasks /delete /tn "AutonovaUpdate" /f 2>nul

:: Clean temp files
echo Cleaning temporary files...
del /f /q "%TEMP%\\autonova_*" 2>nul
del /f /q "%TEMP%\\autonova\\*" 2>nul
rd /s /q "%TEMP%\\autonova" 2>nul

:: Remove logs
del /f /q "%LOCALAPPDATA%\\Autonova\\*.log" 2>nul
rd /s /q "%LOCALAPPDATA%\\Autonova" 2>nul

:: Clean prefetch entries (requires admin)
del /f /q "%WINDIR%\\Prefetch\\AUTONOVA*" 2>nul

:: Clear event logs related to agent (optional, aggressive)
:: wevtutil cl Application 2>nul

echo Cleanup complete!

:: Self-delete this script
(goto) 2>nul & del /f /q "{script_path}"
'''
    
    return script


def create_uninstall_entry() -> bool:
    """
    Create an uninstall entry in Windows Programs and Features.
    This is optional and provides a legitimate uninstall option.
    
    Returns:
        True if successful
    """
    try:
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            return False  # Only for compiled version
        
        uninstall_key = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\AutonovaRMM"
        
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, uninstall_key)
        
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "Autonova RMM Agent")
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.0.0")
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "Autonova")
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{exe_path}" --uninstall')
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        
        winreg.CloseKey(key)
        return True
        
    except Exception:
        return False


def remove_uninstall_entry() -> bool:
    """
    Remove the uninstall entry from Windows.
    
    Returns:
        True if successful or already removed
    """
    try:
        winreg.DeleteKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall\AutonovaRMM"
        )
        return True
    except FileNotFoundError:
        return True
    except Exception:
        return False
