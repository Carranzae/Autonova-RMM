"""
Autonova RMM - Health Check Module
Performs comprehensive system diagnostics using WMI and psutil.
"""

import asyncio
import platform
import socket
from datetime import datetime
from typing import Dict, Any, Optional
import psutil

# WMI is Windows-only
try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False


class HealthChecker:
    """Performs comprehensive Windows system health diagnostics."""
    
    def __init__(self, callback: Optional[callable] = None):
        """
        Initialize the health checker.
        
        Args:
            callback: Optional async function to stream progress updates
        """
        self.callback = callback
        self.wmi_client = wmi.WMI() if WMI_AVAILABLE else None
    
    async def _report(self, message: str, progress: int = 0):
        """Send progress update to callback if available."""
        if self.callback:
            await self.callback({
                "type": "progress",
                "module": "health_check",
                "message": message,
                "progress": progress,
                "timestamp": datetime.now().isoformat()
            })
    
    async def get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU usage and temperature information."""
        await self._report("Analyzing CPU usage...", 10)
        
        cpu_info = {
            "usage_percent": psutil.cpu_percent(interval=1),
            "core_count": psutil.cpu_count(logical=False),
            "thread_count": psutil.cpu_count(logical=True),
            "frequency": {},
            "temperature": None
        }
        
        # CPU frequency
        freq = psutil.cpu_freq()
        if freq:
            cpu_info["frequency"] = {
                "current": round(freq.current, 2),
                "min": round(freq.min, 2),
                "max": round(freq.max, 2)
            }
        
        # CPU temperature (Windows via WMI)
        if self.wmi_client:
            try:
                temps = self.wmi_client.MSAcpi_ThermalZoneTemperature()
                if temps:
                    # Convert from tenths of Kelvin to Celsius
                    temp_celsius = (temps[0].CurrentTemperature / 10) - 273.15
                    cpu_info["temperature"] = round(temp_celsius, 1)
            except Exception:
                # Temperature sensor may not be available
                pass
        
        return cpu_info
    
    async def get_memory_info(self) -> Dict[str, Any]:
        """Get RAM usage statistics."""
        await self._report("Checking memory usage...", 25)
        
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent_used": mem.percent,
            "swap": {
                "total_gb": round(swap.total / (1024**3), 2),
                "used_gb": round(swap.used / (1024**3), 2),
                "percent_used": swap.percent
            }
        }
    
    async def get_disk_info(self) -> Dict[str, Any]:
        """Get disk usage for all partitions."""
        await self._report("Scanning disk partitions...", 40)
        
        disks = []
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "filesystem": partition.fstype,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent_used": usage.percent
                })
            except PermissionError:
                continue
        
        # Disk I/O stats
        io_counters = psutil.disk_io_counters()
        io_stats = None
        if io_counters:
            io_stats = {
                "read_bytes": io_counters.read_bytes,
                "write_bytes": io_counters.write_bytes,
                "read_count": io_counters.read_count,
                "write_count": io_counters.write_count
            }
        
        return {"partitions": disks, "io_stats": io_stats}
    
    async def get_network_info(self) -> Dict[str, Any]:
        """Get network statistics and latency."""
        await self._report("Testing network connectivity...", 60)
        
        # Network interfaces
        interfaces = []
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        
        for iface, addr_list in addrs.items():
            if iface in stats and stats[iface].isup:
                for addr in addr_list:
                    if addr.family == socket.AF_INET:
                        interfaces.append({
                            "name": iface,
                            "ip": addr.address,
                            "netmask": addr.netmask,
                            "speed_mbps": stats[iface].speed
                        })
        
        # Network I/O
        net_io = psutil.net_io_counters()
        io_stats = {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "errors_in": net_io.errin,
            "errors_out": net_io.errout
        }
        
        # Test latency to common DNS servers
        latency = await self._measure_latency()
        
        return {
            "interfaces": interfaces,
            "io_stats": io_stats,
            "latency_ms": latency
        }
    
    async def _measure_latency(self) -> Dict[str, Optional[float]]:
        """Measure network latency to common servers."""
        targets = {
            "google_dns": "8.8.8.8",
            "cloudflare_dns": "1.1.1.1"
        }
        
        results = {}
        for name, ip in targets.items():
            try:
                start = asyncio.get_event_loop().time()
                # Simple TCP connection test
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, 53),
                    timeout=5.0
                )
                latency = (asyncio.get_event_loop().time() - start) * 1000
                writer.close()
                await writer.wait_closed()
                results[name] = round(latency, 2)
            except Exception:
                results[name] = None
        
        return results
    
    async def get_process_info(self) -> Dict[str, Any]:
        """Get top resource-consuming processes."""
        await self._report("Enumerating processes...", 80)
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                if pinfo['cpu_percent'] > 0 or pinfo['memory_percent'] > 1:
                    processes.append({
                        "pid": pinfo['pid'],
                        "name": pinfo['name'],
                        "cpu_percent": round(pinfo['cpu_percent'], 1),
                        "memory_percent": round(pinfo['memory_percent'], 1)
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage and get top 10
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        
        return {
            "total_count": len(list(psutil.process_iter())),
            "top_by_cpu": processes[:10]
        }
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get general system information."""
        await self._report("Gathering system info...", 5)
        
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        return {
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "boot_time": boot_time.isoformat(),
            "uptime_hours": round(uptime.total_seconds() / 3600, 2)
        }
    
    async def run_full_check(self) -> Dict[str, Any]:
        """
        Execute complete health check and return comprehensive report.
        
        Returns:
            Dictionary containing all health metrics
        """
        await self._report("Starting full health check...", 0)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "system": await self.get_system_info(),
            "cpu": await self.get_cpu_info(),
            "memory": await self.get_memory_info(),
            "disk": await self.get_disk_info(),
            "network": await self.get_network_info(),
            "processes": await self.get_process_info()
        }
        
        # Calculate overall health score (0-100)
        score = 100
        
        # Deduct for high CPU usage
        if report["cpu"]["usage_percent"] > 80:
            score -= 20
        elif report["cpu"]["usage_percent"] > 60:
            score -= 10
        
        # Deduct for high memory usage
        if report["memory"]["percent_used"] > 90:
            score -= 25
        elif report["memory"]["percent_used"] > 75:
            score -= 10
        
        # Deduct for low disk space
        for disk in report["disk"]["partitions"]:
            if disk["percent_used"] > 95:
                score -= 20
            elif disk["percent_used"] > 85:
                score -= 10
        
        # Deduct for network issues
        latencies = report["network"]["latency_ms"]
        if all(v is None for v in latencies.values()):
            score -= 15
        
        report["health_score"] = max(0, score)
        
        await self._report("Health check complete!", 100)
        
        return report


async def run_health_check(callback: Optional[callable] = None) -> Dict[str, Any]:
    """
    Convenience function to run a full health check.
    
    Args:
        callback: Optional async function for progress updates
        
    Returns:
        Complete health report dictionary
    """
    checker = HealthChecker(callback)
    return await checker.run_full_check()
