"""
Autonova RMM - Security Module
Exports security and privilege management functionality.
"""

from .elevate import (
    is_admin,
    elevate_privileges,
    run_elevated_command,
    AntiDebug,
    RegistryManager,
    get_security_status
)

__all__ = [
    'is_admin',
    'elevate_privileges',
    'run_elevated_command',
    'AntiDebug',
    'RegistryManager',
    'get_security_status'
]
