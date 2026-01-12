"""
Autonova RMM - Self Destruct / Uninstall Module
Properly removes the agent from the system when work is complete.
"""

import os
import sys
import shutil
import subprocess
import winreg
import ctypes
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)


async def initiate_self_destruct(progress_callback: Callable = None) -> Dict[str, Any]:
    """
    Completely remove the agent from the system.
    This is called when the technician clicks "Finalizar Trabajo".
    """
    results = {
        "success": True,
        "steps_completed": [],
        "errors": []
    }
    
    try:
        if progress_callback:
            await progress_callback({"message": "⚠️ Iniciando proceso de desinstalación...", "percent": 0})
        
        # Step 1: Remove from startup
        if progress_callback:
            await progress_callback({"message": "📝 Eliminando del inicio automático...", "percent": 20})
        
        try:
            remove_from_startup()
            results["steps_completed"].append("startup_removed")
        except Exception as e:
            results["errors"].append(f"Startup removal: {e}")
        
        # Step 2: Remove scheduled tasks
        if progress_callback:
            await progress_callback({"message": "📅 Eliminando tareas programadas...", "percent": 40})
        
        try:
            remove_scheduled_tasks()
            results["steps_completed"].append("tasks_removed")
        except Exception as e:
            results["errors"].append(f"Task removal: {e}")
        
        # Step 3: Remove config files
        if progress_callback:
            await progress_callback({"message": "🗑️ Eliminando archivos de configuración...", "percent": 60})
        
        try:
            remove_config_files()
            results["steps_completed"].append("config_removed")
        except Exception as e:
            results["errors"].append(f"Config removal: {e}")
        
        # Step 4: Create self-delete batch script
        if progress_callback:
            await progress_callback({"message": "📄 Preparando eliminación del ejecutable...", "percent": 80})
        
        try:
            create_self_delete_script()
            results["steps_completed"].append("self_delete_prepared")
        except Exception as e:
            results["errors"].append(f"Self-delete: {e}")
        
        if progress_callback:
            await progress_callback({"message": "✅ Desinstalación completada. El agente se cerrará.", "percent": 100})
        
        await asyncio.sleep(2)
        
        # Exit the application - the batch script will delete the exe
        logger.info("Self-destruct initiated. Exiting...")
        os._exit(0)
        
    except Exception as e:
        logger.error(f"Self-destruct error: {e}")
        results["success"] = False
        results["errors"].append(str(e))
        return results
    
    return results


def remove_from_startup():
    """Remove agent from Windows startup."""
    try:
        # Remove from registry Run key
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, "AutonovaAgent")
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
        except:
            pass
        
        # Remove from startup folder
        startup_folder = Path(os.environ.get('APPDATA', '')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'
        for file in startup_folder.glob("*autonova*"):
            try:
                file.unlink()
            except:
                pass
        
        logger.info("Removed from startup")
    except Exception as e:
        logger.error(f"Error removing from startup: {e}")


def remove_scheduled_tasks():
    """Remove any scheduled tasks created by the agent."""
    try:
        task_names = ["AutonovaAgent", "AutonovaRMM", "AutonovaHealthCheck"]
        for task in task_names:
            try:
                subprocess.run(
                    ["schtasks", "/delete", "/tn", task, "/f"],
                    capture_output=True,
                    timeout=10
                )
            except:
                pass
        logger.info("Scheduled tasks removed")
    except Exception as e:
        logger.error(f"Error removing scheduled tasks: {e}")


def remove_config_files():
    """Remove configuration and log files."""
    try:
        config_dir = Path(os.environ.get('LOCALAPPDATA', '')) / 'Autonova'
        if config_dir.exists():
            shutil.rmtree(config_dir, ignore_errors=True)
        
        # Also remove any temp files
        temp_dir = Path(os.environ.get('TEMP', '')) / 'Autonova'
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        logger.info("Config files removed")
    except Exception as e:
        logger.error(f"Error removing config files: {e}")


def create_self_delete_script():
    """Create a batch script that will delete the exe after it exits."""
    try:
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            # Not running as exe, skip
            return
        
        # Create batch script in temp
        batch_content = f'''@echo off
timeout /t 3 /nobreak > nul
del /f /q "{exe_path}"
del /f /q "%~f0"
'''
        
        batch_path = Path(os.environ.get('TEMP', '')) / 'autonova_cleanup.bat'
        with open(batch_path, 'w') as f:
            f.write(batch_content)
        
        # Run the batch script hidden
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        subprocess.Popen(
            ['cmd', '/c', str(batch_path)],
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        logger.info("Self-delete script created and executed")
    except Exception as e:
        logger.error(f"Error creating self-delete script: {e}")


async def force_uninstall_program(program_name: str, progress_callback: Callable = None) -> Dict[str, Any]:
    """
    Force uninstall a program by name.
    Uses multiple methods to ensure removal.
    """
    results = {
        "success": False,
        "program": program_name,
        "method_used": None,
        "message": ""
    }
    
    if progress_callback:
        await progress_callback({"message": f"🔍 Buscando {program_name}...", "percent": 10})
    
    # Method 1: Try WMIC uninstall
    try:
        if progress_callback:
            await progress_callback({"message": f"🗑️ Intentando desinstalar {program_name}...", "percent": 30})
        
        result = subprocess.run(
            ['wmic', 'product', 'where', f'name like "%{program_name}%"', 'call', 'uninstall', '/nointeractive'],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if "ReturnValue = 0" in result.stdout or "Method execution successful" in result.stdout:
            results["success"] = True
            results["method_used"] = "wmic"
            results["message"] = f"✅ {program_name} desinstalado exitosamente"
            if progress_callback:
                await progress_callback({"message": results["message"], "percent": 100})
            return results
    except Exception as e:
        logger.debug(f"WMIC method failed: {e}")
    
    # Method 2: Try using PowerShell
    try:
        if progress_callback:
            await progress_callback({"message": f"🔧 Usando PowerShell para {program_name}...", "percent": 50})
        
        ps_command = f'''
        $app = Get-WmiObject -Class Win32_Product | Where-Object {{ $_.Name -like "*{program_name}*" }}
        if ($app) {{
            $app.Uninstall()
            Write-Output "Uninstalled"
        }}
        '''
        
        result = subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_command],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if "Uninstalled" in result.stdout:
            results["success"] = True
            results["method_used"] = "powershell"
            results["message"] = f"✅ {program_name} desinstalado con PowerShell"
            if progress_callback:
                await progress_callback({"message": results["message"], "percent": 100})
            return results
    except Exception as e:
        logger.debug(f"PowerShell method failed: {e}")
    
    # Method 3: Search registry for uninstall string
    try:
        if progress_callback:
            await progress_callback({"message": f"📝 Buscando en registro {program_name}...", "percent": 70})
        
        uninstall_string = find_uninstall_string(program_name)
        if uninstall_string:
            subprocess.run(uninstall_string, shell=True, timeout=120)
            results["success"] = True
            results["method_used"] = "registry"
            results["message"] = f"✅ {program_name} desinstalado via registro"
            if progress_callback:
                await progress_callback({"message": results["message"], "percent": 100})
            return results
    except Exception as e:
        logger.debug(f"Registry method failed: {e}")
    
    results["message"] = f"⚠️ No se pudo desinstalar {program_name} automáticamente"
    if progress_callback:
        await progress_callback({"message": results["message"], "percent": 100})
    
    return results


def find_uninstall_string(program_name: str) -> str:
    """Find uninstall string in registry."""
    uninstall_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
    ]
    
    for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
        for path in uninstall_paths:
            try:
                key = winreg.OpenKey(root, path)
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(key, subkey_name)
                        try:
                            name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                            if program_name.lower() in name.lower():
                                uninstall, _ = winreg.QueryValueEx(subkey, "UninstallString")
                                return uninstall
                        except:
                            pass
                        winreg.CloseKey(subkey)
                    except:
                        pass
                winreg.CloseKey(key)
            except:
                pass
    return None


async def kill_process_by_name(process_name: str, progress_callback: Callable = None) -> Dict[str, Any]:
    """Kill a process by name."""
    results = {"success": False, "killed": 0}
    
    try:
        if progress_callback:
            await progress_callback({"message": f"🔪 Terminando proceso {process_name}...", "percent": 50})
        
        result = subprocess.run(
            ['taskkill', '/f', '/im', process_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            results["success"] = True
            results["message"] = f"✅ Proceso {process_name} terminado"
        else:
            results["message"] = f"⚠️ No se encontró el proceso {process_name}"
        
        if progress_callback:
            await progress_callback({"message": results["message"], "percent": 100})
        
    except Exception as e:
        results["message"] = f"❌ Error: {e}"
    
    return results


async def list_installed_programs(progress_callback: Callable = None) -> Dict[str, Any]:
    """List all installed programs."""
    programs = []
    
    if progress_callback:
        await progress_callback({"message": "📋 Obteniendo lista de programas...", "percent": 20})
    
    uninstall_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    
    for root, path in uninstall_paths:
        try:
            key = winreg.OpenKey(root, path)
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkey = winreg.OpenKey(key, subkey_name)
                    try:
                        name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                        try:
                            version, _ = winreg.QueryValueEx(subkey, "DisplayVersion")
                        except:
                            version = "N/A"
                        
                        if name and name not in [p["name"] for p in programs]:
                            programs.append({"name": name, "version": version})
                    except:
                        pass
                    winreg.CloseKey(subkey)
                except:
                    pass
            winreg.CloseKey(key)
        except:
            pass
    
    programs.sort(key=lambda x: x["name"].lower())
    
    if progress_callback:
        await progress_callback({"message": f"✅ {len(programs)} programas encontrados", "percent": 100})
    
    return {"success": True, "programs": programs, "count": len(programs)}
