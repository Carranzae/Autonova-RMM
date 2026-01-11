"""
Autonova RMM - System Fixer Module
Executes Windows repair commands: SFC, DISM, Network Reset.
Uses subprocess.Popen to capture live output for streaming.
"""

import asyncio
import subprocess
import re
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator
from enum import Enum


class RepairCommand(Enum):
    """Available repair commands."""
    SFC = "sfc"
    DISM_HEALTH = "dism_health"
    DISM_RESTORE = "dism_restore"
    CHKDSK = "chkdsk"
    NET_RESET = "net_reset"
    DNS_FLUSH = "dns_flush"
    WINSOCK_RESET = "winsock_reset"


class SystemFixer:
    """Executes Windows system repair commands with live output streaming."""
    
    # Command definitions
    COMMANDS = {
        RepairCommand.SFC: {
            "cmd": ["sfc", "/scannow"],
            "description": "System File Checker - Scans and repairs system files",
            "requires_admin": True,
            "timeout": 1800  # 30 minutes
        },
        RepairCommand.DISM_HEALTH: {
            "cmd": ["DISM", "/Online", "/Cleanup-Image", "/CheckHealth"],
            "description": "DISM - Check component store health",
            "requires_admin": True,
            "timeout": 300
        },
        RepairCommand.DISM_RESTORE: {
            "cmd": ["DISM", "/Online", "/Cleanup-Image", "/RestoreHealth"],
            "description": "DISM - Restore component store health",
            "requires_admin": True,
            "timeout": 3600  # 60 minutes
        },
        RepairCommand.CHKDSK: {
            "cmd": ["chkdsk", "C:", "/scan"],
            "description": "Check Disk - Scan for filesystem errors",
            "requires_admin": True,
            "timeout": 1800
        },
        RepairCommand.NET_RESET: {
            "cmd": ["netsh", "int", "ip", "reset"],
            "description": "Reset TCP/IP stack",
            "requires_admin": True,
            "timeout": 60
        },
        RepairCommand.DNS_FLUSH: {
            "cmd": ["ipconfig", "/flushdns"],
            "description": "Flush DNS resolver cache",
            "requires_admin": False,
            "timeout": 30
        },
        RepairCommand.WINSOCK_RESET: {
            "cmd": ["netsh", "winsock", "reset"],
            "description": "Reset Winsock catalog",
            "requires_admin": True,
            "timeout": 60
        }
    }
    
    def __init__(self, callback: Optional[callable] = None):
        """
        Initialize the system fixer.
        
        Args:
            callback: Optional async function for progress/output updates
        """
        self.callback = callback
        self.current_process: Optional[subprocess.Popen] = None
        self.cancelled = False
    
    async def _report(self, message: str, output_type: str = "info", progress: int = 0):
        """Send progress/output update to callback."""
        if self.callback:
            await self.callback({
                "type": output_type,
                "module": "sys_fixer",
                "message": message,
                "progress": progress,
                "timestamp": datetime.now().isoformat()
            })
    
    async def _stream_output(self, process: subprocess.Popen, command_name: str) -> str:
        """
        Stream live output from a running process.
        
        Args:
            process: Running subprocess
            command_name: Name of command for logging
            
        Returns:
            Complete output as string
        """
        full_output = []
        
        while True:
            if self.cancelled:
                process.terminate()
                break
            
            # Read line from stdout
            line = await asyncio.get_event_loop().run_in_executor(
                None, process.stdout.readline
            )
            
            if not line and process.poll() is not None:
                break
            
            if line:
                decoded_line = line.decode('utf-8', errors='ignore').strip()
                if decoded_line:
                    full_output.append(decoded_line)
                    await self._report(decoded_line, "output")
        
        # Get any remaining output
        remaining, _ = process.communicate()
        if remaining:
            for line in remaining.decode('utf-8', errors='ignore').split('\n'):
                if line.strip():
                    full_output.append(line.strip())
        
        return '\n'.join(full_output)
    
    async def run_command(self, command: RepairCommand) -> Dict[str, Any]:
        """
        Execute a single repair command with live output streaming.
        
        Args:
            command: The repair command to execute
            
        Returns:
            Command execution result
        """
        cmd_config = self.COMMANDS[command]
        
        await self._report(
            f"Starting: {cmd_config['description']}",
            "info"
        )
        
        result = {
            "command": command.value,
            "description": cmd_config["description"],
            "started_at": datetime.now().isoformat(),
            "success": False,
            "return_code": None,
            "output": "",
            "error": None
        }
        
        try:
            # Start the process
            self.current_process = subprocess.Popen(
                cmd_config["cmd"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Stream output
            result["output"] = await asyncio.wait_for(
                self._stream_output(self.current_process, command.value),
                timeout=cmd_config["timeout"]
            )
            
            result["return_code"] = self.current_process.returncode
            result["success"] = self.current_process.returncode == 0
            
        except asyncio.TimeoutError:
            result["error"] = f"Command timed out after {cmd_config['timeout']} seconds"
            if self.current_process:
                self.current_process.terminate()
        except Exception as e:
            result["error"] = str(e)
        finally:
            result["completed_at"] = datetime.now().isoformat()
            self.current_process = None
        
        await self._report(
            f"Completed: {command.value} - {'Success' if result['success'] else 'Failed'}",
            "info"
        )
        
        return result
    
    async def run_sfc_scan(self) -> Dict[str, Any]:
        """Run System File Checker (sfc /scannow)."""
        await self._report("Running System File Checker...", "info", 10)
        result = await self.run_command(RepairCommand.SFC)
        
        # Parse SFC output for summary
        if result["output"]:
            if "did not find any integrity violations" in result["output"].lower():
                result["summary"] = "No integrity violations found"
            elif "successfully repaired" in result["output"].lower():
                result["summary"] = "Issues found and repaired"
            elif "could not perform the requested operation" in result["output"].lower():
                result["summary"] = "SFC could not complete - may need DISM first"
            else:
                result["summary"] = "Scan completed"
        
        return result
    
    async def run_dism_repair(self) -> Dict[str, Any]:
        """Run full DISM repair sequence."""
        await self._report("Running DISM repair sequence...", "info", 30)
        
        # First check health
        health_result = await self.run_command(RepairCommand.DISM_HEALTH)
        
        results = {
            "health_check": health_result,
            "restore": None
        }
        
        # If issues found or check passed, run restore
        await self._report("Running DISM restore...", "info", 50)
        results["restore"] = await self.run_command(RepairCommand.DISM_RESTORE)
        
        return results
    
    async def run_network_reset(self) -> Dict[str, Any]:
        """Run complete network reset sequence."""
        await self._report("Running network reset sequence...", "info", 70)
        
        results = {
            "dns_flush": None,
            "winsock_reset": None,
            "ip_reset": None,
            "requires_restart": False
        }
        
        # Flush DNS
        await self._report("Flushing DNS cache...", "info", 75)
        results["dns_flush"] = await self.run_command(RepairCommand.DNS_FLUSH)
        
        # Reset Winsock
        await self._report("Resetting Winsock catalog...", "info", 85)
        results["winsock_reset"] = await self.run_command(RepairCommand.WINSOCK_RESET)
        if results["winsock_reset"]["success"]:
            results["requires_restart"] = True
        
        # Reset IP stack
        await self._report("Resetting TCP/IP stack...", "info", 95)
        results["ip_reset"] = await self.run_command(RepairCommand.NET_RESET)
        if results["ip_reset"]["success"]:
            results["requires_restart"] = True
        
        return results
    
    async def run_full_repair(self) -> Dict[str, Any]:
        """
        Execute complete system repair sequence.
        
        Returns:
            Complete repair report with all command results
        """
        await self._report("Starting full system repair...", "info", 0)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "sfc": await self.run_sfc_scan(),
            "dism": await self.run_dism_repair(),
            "network": await self.run_network_reset(),
            "requires_restart": False
        }
        
        # Check if restart is needed
        if report["network"].get("requires_restart"):
            report["requires_restart"] = True
        
        # Calculate overall success
        all_results = [
            report["sfc"]["success"],
            report["dism"]["restore"]["success"] if report["dism"]["restore"] else False,
            report["network"]["dns_flush"]["success"] if report["network"]["dns_flush"] else False
        ]
        report["overall_success"] = all(all_results)
        
        await self._report(
            "Full system repair complete!" + 
            (" Restart required." if report["requires_restart"] else ""),
            "info",
            100
        )
        
        return report
    
    def cancel(self):
        """Cancel the current running command."""
        self.cancelled = True
        if self.current_process:
            self.current_process.terminate()


async def run_sys_fix(callback: Optional[callable] = None) -> Dict[str, Any]:
    """
    Convenience function to run full system repair.
    
    Args:
        callback: Optional async function for progress updates
        
    Returns:
        Complete repair report
    """
    fixer = SystemFixer(callback)
    return await fixer.run_full_repair()
