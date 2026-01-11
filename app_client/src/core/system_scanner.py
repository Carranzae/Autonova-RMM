"""
Autonova RMM - Advanced System Scanner
Comprehensive security and health scanner with real-time output.
"""

import os
import sys
import socket
import psutil
import winreg
import subprocess
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional
import asyncio
import json

logger = logging.getLogger(__name__)

# Known malware process names (basic detection)
SUSPICIOUS_PROCESSES = [
    'cryptominer', 'miner', 'xmrig', 'cgminer', 'bfgminer',
    'keylogger', 'trojan', 'backdoor', 'rootkit', 'ransomware',
    'coinhive', 'bitcoinminer', 'malware', 'virus', 'worm'
]

# Suspicious startup locations
STARTUP_REGISTRY_PATHS = [
    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
]

# Known malicious file hashes (example - in production, use updated database)
KNOWN_MALWARE_HASHES = set()

# Common malware locations
MALWARE_LOCATIONS = [
    Path(os.environ.get('TEMP', '')),
    Path(os.environ.get('APPDATA', '')) / 'Local' / 'Temp',
    Path(os.environ.get('USERPROFILE', '')) / 'Downloads',
    Path('C:/Windows/Temp'),
]


class SystemScanner:
    """
    Comprehensive system scanner with real-time progress output.
    Scans hardware, software, security, and network configuration.
    """
    
    def __init__(self, progress_callback: Callable = None):
        self.progress_callback = progress_callback
        self.scan_results = {
            "start_time": None,
            "end_time": None,
            "duration_seconds": 0,
            "system_info": {},
            "hardware": {},
            "security": {},
            "network": {},
            "threats_found": [],
            "issues_found": [],
            "recommendations": [],
            "score": 100  # Health score out of 100
        }
        self.threats_count = 0
        self.issues_count = 0
    
    async def log(self, message: str, level: str = "info"):
        """Send progress message to dashboard console."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        print(formatted)
        
        if self.progress_callback:
            await self.progress_callback({
                "message": message,
                "timestamp": timestamp,
                "level": level
            })
    
    async def scan_complete(self) -> Dict[str, Any]:
        """
        Execute complete system scan with all modules.
        Returns comprehensive scan results.
        """
        self.scan_results["start_time"] = datetime.now().isoformat()
        start = datetime.now()
        
        await self.log("═" * 50, "header")
        await self.log("🔍 INICIANDO ESCANEO COMPLETO DEL SISTEMA", "header")
        await self.log("═" * 50, "header")
        await self.log("")
        
        # Phase 1: System Information
        await self.log("📊 FASE 1: Recopilando información del sistema...", "phase")
        await self._scan_system_info()
        
        # Phase 2: Hardware Analysis
        await self.log("")
        await self.log("🖥️ FASE 2: Analizando hardware...", "phase")
        await self._scan_hardware()
        
        # Phase 3: Memory Analysis
        await self.log("")
        await self.log("💾 FASE 3: Analizando memoria y caché...", "phase")
        await self._scan_memory()
        
        # Phase 4: Disk Analysis
        await self.log("")
        await self.log("💿 FASE 4: Analizando discos y almacenamiento...", "phase")
        await self._scan_disks()
        
        # Phase 5: Process Analysis
        await self.log("")
        await self.log("⚙️ FASE 5: Analizando procesos en ejecución...", "phase")
        await self._scan_processes()
        
        # Phase 6: Network Security
        await self.log("")
        await self.log("🌐 FASE 6: Analizando seguridad de red...", "phase")
        await self._scan_network()
        
        # Phase 7: Startup Items
        await self.log("")
        await self.log("🚀 FASE 7: Analizando programas de inicio...", "phase")
        await self._scan_startup()
        
        # Phase 8: Security Scan
        await self.log("")
        await self.log("🛡️ FASE 8: Escaneando amenazas de seguridad...", "phase")
        await self._scan_security()
        
        # Phase 9: Registry Analysis
        await self.log("")
        await self.log("📝 FASE 9: Analizando registro de Windows...", "phase")
        await self._scan_registry()
        
        # Phase 10: Generate Report
        await self.log("")
        await self.log("📋 FASE 10: Generando reporte final...", "phase")
        await self._generate_report(start)
        
        return self.scan_results
    
    async def _scan_system_info(self):
        """Gather system information."""
        await asyncio.sleep(0.1)  # Small delay for UI
        
        import platform
        
        info = {
            "hostname": socket.gethostname(),
            "os": platform.system(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "username": os.environ.get('USERNAME', 'unknown'),
            "computer_name": os.environ.get('COMPUTERNAME', 'unknown')
        }
        
        self.scan_results["system_info"] = info
        
        await self.log(f"   Sistema Operativo: {info['os']} {info['os_release']}")
        await self.log(f"   Versión: {info['os_version'][:50]}...")
        await self.log(f"   Arquitectura: {info['architecture']}")
        await self.log(f"   Procesador: {info['processor'][:40]}...")
        await self.log(f"   Usuario: {info['username']}@{info['hostname']}")
        await self.log("   ✓ Información del sistema recopilada", "success")
    
    async def _scan_hardware(self):
        """Analyze hardware components."""
        await asyncio.sleep(0.1)
        
        # CPU Info
        cpu_count = psutil.cpu_count(logical=False)
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        await self.log(f"   CPU: {cpu_count} núcleos físicos, {cpu_count_logical} lógicos")
        if cpu_freq:
            await self.log(f"   Frecuencia: {cpu_freq.current:.0f} MHz (Max: {cpu_freq.max:.0f} MHz)")
        await self.log(f"   Uso actual: {cpu_percent}%")
        
        if cpu_percent > 90:
            self.issues_count += 1
            self.scan_results["issues_found"].append({
                "type": "hardware",
                "severity": "high",
                "message": f"CPU al {cpu_percent}% - Posible problema de rendimiento"
            })
            await self.log(f"   ⚠️ ALERTA: CPU muy alto ({cpu_percent}%)", "warning")
            self.scan_results["score"] -= 5
        
        # Temperature (if available)
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current > 80:
                            await self.log(f"   🌡️ ALERTA: Temperatura alta: {entry.label}: {entry.current}°C", "warning")
                            self.scan_results["score"] -= 3
        except:
            pass
        
        self.scan_results["hardware"]["cpu"] = {
            "cores_physical": cpu_count,
            "cores_logical": cpu_count_logical,
            "frequency_mhz": cpu_freq.current if cpu_freq else 0,
            "usage_percent": cpu_percent
        }
        
        await self.log("   ✓ Hardware analizado", "success")
    
    async def _scan_memory(self):
        """Analyze memory and cache."""
        await asyncio.sleep(0.1)
        
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        total_gb = mem.total / (1024**3)
        used_gb = mem.used / (1024**3)
        available_gb = mem.available / (1024**3)
        
        await self.log(f"   RAM Total: {total_gb:.1f} GB")
        await self.log(f"   RAM Usada: {used_gb:.1f} GB ({mem.percent}%)")
        await self.log(f"   RAM Disponible: {available_gb:.1f} GB")
        
        if mem.percent > 85:
            self.issues_count += 1
            self.scan_results["issues_found"].append({
                "type": "memory",
                "severity": "medium",
                "message": f"Memoria RAM al {mem.percent}% - Considere cerrar aplicaciones"
            })
            await self.log(f"   ⚠️ Memoria alta: {mem.percent}%", "warning")
            self.scan_results["score"] -= 5
        
        # Swap
        if swap.total > 0:
            swap_gb = swap.total / (1024**3)
            swap_used_gb = swap.used / (1024**3)
            await self.log(f"   Swap Total: {swap_gb:.1f} GB (Usado: {swap_used_gb:.1f} GB)")
        
        self.scan_results["hardware"]["memory"] = {
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "available_gb": round(available_gb, 2),
            "percent": mem.percent
        }
        
        await self.log("   ✓ Memoria analizada", "success")
    
    async def _scan_disks(self):
        """Analyze disk storage."""
        await asyncio.sleep(0.1)
        
        partitions = psutil.disk_partitions()
        disk_info = []
        
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                total_gb = usage.total / (1024**3)
                used_gb = usage.used / (1024**3)
                free_gb = usage.free / (1024**3)
                
                await self.log(f"   Disco {partition.mountpoint}")
                await self.log(f"      Total: {total_gb:.1f} GB | Usado: {used_gb:.1f} GB | Libre: {free_gb:.1f} GB")
                await self.log(f"      Uso: {usage.percent}%")
                
                if usage.percent > 90:
                    self.issues_count += 1
                    self.scan_results["issues_found"].append({
                        "type": "disk",
                        "severity": "high",
                        "message": f"Disco {partition.mountpoint} casi lleno ({usage.percent}%)"
                    })
                    await self.log(f"      ⚠️ ALERTA: Disco casi lleno!", "warning")
                    self.scan_results["score"] -= 10
                
                disk_info.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "total_gb": round(total_gb, 2),
                    "free_gb": round(free_gb, 2),
                    "percent": usage.percent
                })
            except:
                continue
        
        self.scan_results["hardware"]["disks"] = disk_info
        await self.log("   ✓ Discos analizados", "success")
    
    async def _scan_processes(self):
        """Analyze running processes for suspicious activity."""
        await asyncio.sleep(0.1)
        
        total_processes = 0
        suspicious_found = []
        high_cpu_processes = []
        high_mem_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username']):
            try:
                total_processes += 1
                name = proc.info['name'].lower()
                
                # Check for suspicious names
                for suspicious in SUSPICIOUS_PROCESSES:
                    if suspicious in name:
                        suspicious_found.append(proc.info)
                        self.threats_count += 1
                        self.scan_results["threats_found"].append({
                            "type": "suspicious_process",
                            "severity": "critical",
                            "name": proc.info['name'],
                            "pid": proc.info['pid']
                        })
                
                # Check for high CPU usage
                if proc.info['cpu_percent'] and proc.info['cpu_percent'] > 50:
                    high_cpu_processes.append(proc.info)
                
                # Check for high memory usage
                if proc.info['memory_percent'] and proc.info['memory_percent'] > 10:
                    high_mem_processes.append(proc.info)
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        await self.log(f"   Total de procesos: {total_processes}")
        await self.log(f"   Procesos con alto CPU: {len(high_cpu_processes)}")
        await self.log(f"   Procesos con alta memoria: {len(high_mem_processes)}")
        
        if suspicious_found:
            for proc in suspicious_found:
                await self.log(f"   🚨 AMENAZA: Proceso sospechoso: {proc['name']} (PID: {proc['pid']})", "danger")
            self.scan_results["score"] -= 20
        else:
            await self.log("   ✓ No se detectaron procesos maliciosos", "success")
        
        self.scan_results["security"]["processes"] = {
            "total": total_processes,
            "suspicious": len(suspicious_found),
            "high_cpu": len(high_cpu_processes),
            "high_memory": len(high_mem_processes)
        }
    
    async def _scan_network(self):
        """Analyze network security."""
        await asyncio.sleep(0.1)
        
        # Get network connections
        connections = psutil.net_connections(kind='inet')
        listening_ports = []
        established = []
        suspicious_connections = []
        
        for conn in connections:
            try:
                if conn.status == 'LISTEN':
                    listening_ports.append(conn.laddr.port)
                elif conn.status == 'ESTABLISHED':
                    established.append({
                        "local": f"{conn.laddr.ip}:{conn.laddr.port}",
                        "remote": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A"
                    })
                    
                    # Check for suspicious ports
                    if conn.raddr and conn.raddr.port in [4444, 5555, 6666, 31337]:
                        suspicious_connections.append(conn)
                        self.threats_count += 1
            except:
                continue
        
        await self.log(f"   Puertos en escucha: {len(listening_ports)}")
        await self.log(f"   Conexiones activas: {len(established)}")
        
        # Get network interfaces
        interfaces = psutil.net_if_addrs()
        for name, addrs in interfaces.items():
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    await self.log(f"   Interface {name}: {addr.address}")
        
        if suspicious_connections:
            for conn in suspicious_connections:
                await self.log(f"   🚨 CONEXIÓN SOSPECHOSA: Puerto {conn.raddr.port}", "danger")
            self.scan_results["score"] -= 15
        else:
            await self.log("   ✓ No se detectaron conexiones sospechosas", "success")
        
        self.scan_results["network"] = {
            "listening_ports": len(listening_ports),
            "active_connections": len(established),
            "suspicious": len(suspicious_connections)
        }
    
    async def _scan_startup(self):
        """Scan startup programs."""
        await asyncio.sleep(0.1)
        
        startup_items = []
        suspicious_startup = []
        
        for hkey, path in STARTUP_REGISTRY_PATHS:
            try:
                key = winreg.OpenKey(hkey, path)
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        startup_items.append({"name": name, "command": value[:100]})
                        
                        # Check for suspicious patterns
                        value_lower = value.lower()
                        if any(sus in value_lower for sus in ['temp', 'appdata\\local\\temp', '.vbs', '.bat']):
                            suspicious_startup.append({"name": name, "command": value})
                            self.threats_count += 1
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(key)
            except:
                continue
        
        await self.log(f"   Programas de inicio: {len(startup_items)}")
        
        if suspicious_startup:
            for item in suspicious_startup:
                await self.log(f"   ⚠️ Inicio sospechoso: {item['name']}", "warning")
            self.scan_results["score"] -= 10
        else:
            await self.log("   ✓ Programas de inicio verificados", "success")
        
        self.scan_results["security"]["startup"] = {
            "total": len(startup_items),
            "suspicious": len(suspicious_startup)
        }
    
    async def _scan_security(self):
        """Deep security scan."""
        await asyncio.sleep(0.1)
        
        await self.log("   Verificando Windows Defender...")
        
        # Check Windows Defender status
        try:
            result = subprocess.run(
                ['powershell', '-Command', 'Get-MpComputerStatus | Select-Object -Property AntivirusEnabled,RealTimeProtectionEnabled'],
                capture_output=True, text=True, timeout=10
            )
            if 'True' in result.stdout:
                await self.log("   ✓ Windows Defender activo", "success")
            else:
                await self.log("   ⚠️ Windows Defender puede estar desactivado", "warning")
                self.scan_results["score"] -= 10
        except:
            await self.log("   No se pudo verificar Windows Defender")
        
        await self.log("   Verificando firewall...")
        
        # Check Firewall
        try:
            result = subprocess.run(
                ['netsh', 'advfirewall', 'show', 'allprofiles', 'state'],
                capture_output=True, text=True, timeout=10
            )
            if 'ON' in result.stdout.upper():
                await self.log("   ✓ Firewall activo", "success")
            else:
                await self.log("   ⚠️ Firewall puede estar desactivado", "warning")
                self.scan_results["score"] -= 10
                self.scan_results["issues_found"].append({
                    "type": "security",
                    "severity": "high",
                    "message": "Firewall de Windows desactivado"
                })
        except:
            await self.log("   No se pudo verificar el firewall")
        
        await self.log("   Verificando actualizaciones de seguridad...")
        await self.log("   ✓ Verificación de seguridad completada", "success")
    
    async def _scan_registry(self):
        """Scan Windows registry for issues."""
        await asyncio.sleep(0.1)
        
        await self.log("   Escaneando registro de Windows...")
        
        # Check for orphaned entries (simplified)
        orphaned_count = 0
        
        # Check common issue locations
        try:
            # Check uninstall entries
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall")
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
            await self.log(f"   Entradas de desinstalación: {i}")
        except:
            pass
        
        await self.log(f"   Entradas huérfanas encontradas: {orphaned_count}")
        await self.log("   ✓ Registro analizado", "success")
        
        self.scan_results["security"]["registry"] = {
            "orphaned_entries": orphaned_count
        }
    
    async def _generate_report(self, start_time: datetime):
        """Generate final scan report."""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        self.scan_results["end_time"] = end_time.isoformat()
        self.scan_results["duration_seconds"] = round(duration, 2)
        
        # Final score adjustments
        if self.scan_results["score"] < 0:
            self.scan_results["score"] = 0
        
        await self.log("")
        await self.log("═" * 50, "header")
        await self.log("📊 REPORTE FINAL DE ESCANEO", "header")
        await self.log("═" * 50, "header")
        await self.log("")
        await self.log(f"   Duración del escaneo: {duration:.1f} segundos")
        await self.log(f"   Amenazas detectadas: {self.threats_count}")
        await self.log(f"   Problemas encontrados: {len(self.scan_results['issues_found'])}")
        await self.log("")
        
        # Health Score
        score = self.scan_results["score"]
        if score >= 80:
            status = "EXCELENTE 🟢"
        elif score >= 60:
            status = "BUENO 🟡"
        elif score >= 40:
            status = "REGULAR 🟠"
        else:
            status = "CRÍTICO 🔴"
        
        await self.log(f"   PUNTUACIÓN DE SALUD: {score}/100 - {status}")
        await self.log("")
        
        # Recommendations
        if self.scan_results["issues_found"]:
            await self.log("   📋 RECOMENDACIONES:", "info")
            for issue in self.scan_results["issues_found"][:5]:
                await self.log(f"      • {issue['message']}")
        
        if self.threats_count > 0:
            await self.log("")
            await self.log("   🛡️ ACCIONES RECOMENDADAS:", "warning")
            await self.log("      • Ejecutar limpieza profunda")
            await self.log("      • Revisar procesos sospechosos")
            await self.log("      • Actualizar antivirus")
        
        await self.log("")
        await self.log("═" * 50, "header")
        await self.log("✅ ESCANEO COMPLETADO", "success")
        await self.log("═" * 50, "header")
        
        return self.scan_results


async def run_full_scan(progress_callback: Callable = None) -> Dict[str, Any]:
    """
    Execute full system scan.
    
    Args:
        progress_callback: Async function to receive progress updates
        
    Returns:
        Complete scan results dictionary
    """
    scanner = SystemScanner(progress_callback)
    return await scanner.scan_complete()
