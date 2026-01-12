"""
Autonova RMM - Commands API
REST endpoints for sending commands to agents.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from api.auth import get_current_active_user, require_admin, User
from sockets.agent_socket import connected_agents, send_command_to_agent

router = APIRouter()


class CommandRequest(BaseModel):
    """Command request model."""
    agent_id: str
    command_type: str  # health_check, deep_clean, sys_fix, full_optimize, self_destruct
    params: dict = {}


class CommandResponse(BaseModel):
    """Command response model."""
    command_id: str
    agent_id: str
    command_type: str
    status: str
    created_at: str


class AgentInfo(BaseModel):
    """Agent information model."""
    agent_id: str
    hostname: Optional[str] = None
    username: Optional[str] = None
    connected_at: str
    last_heartbeat: Optional[str] = None
    status: str


@router.get("/agents", response_model=List[AgentInfo])
async def list_agents(current_user: User = Depends(get_current_active_user)):
    """
    List all connected agents.
    """
    agents = []
    for agent_id, info in connected_agents.items():
        agents.append(AgentInfo(
            agent_id=agent_id,
            hostname=info.get("hostname"),
            username=info.get("username"),
            connected_at=info.get("connected_at", ""),
            last_heartbeat=info.get("last_heartbeat"),
            status="online" if info.get("online", False) else "offline"
        ))
    
    return agents


@router.get("/agents/{agent_id}")
async def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get details for a specific agent.
    """
    if agent_id not in connected_agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    info = connected_agents[agent_id]
    return AgentInfo(
        agent_id=agent_id,
        hostname=info.get("hostname"),
        username=info.get("username"),
        connected_at=info.get("connected_at", ""),
        last_heartbeat=info.get("last_heartbeat"),
        status="online" if info.get("online", False) else "offline"
    )


@router.post("/command", response_model=CommandResponse)
async def send_command(
    request: CommandRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin)
):
    """
    Send a command to an agent.
    Requires admin privileges.
    """
    # Validate agent exists
    if request.agent_id not in connected_agents:
        raise HTTPException(status_code=404, detail="Agent not found or offline")
    
    if not connected_agents[request.agent_id].get("online", False):
        raise HTTPException(status_code=400, detail="Agent is offline")
    
    # Validate command type
    valid_commands = [
        # Core commands
        'health_check', 'deep_clean', 'sys_fix', 'full_optimize', 'self_destruct',
        'view_processes', 'analyze_disk', 'force_delete', 'clean_registry',
        'speed_up_boot', 'network_reset', 'generate_report',
        # Advanced control commands  
        'list_programs', 'force_uninstall', 'kill_process',
        # File explorer commands
        'browse_files', 'view_downloads', 'view_recycle_bin', 'delete_file',
        # Security scanning commands
        'scan_browser_history', 'scan_threats', 'scan_network'
    ]
    if request.command_type not in valid_commands:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid command. Valid commands: {', '.join(valid_commands)}"
        )
    
    # Self-destruct requires special confirmation
    if request.command_type == 'self_destruct':
        if not request.params.get('confirm'):
            raise HTTPException(
                status_code=400,
                detail="Self-destruct requires 'confirm': true in params"
            )
    
    # Create command
    command_id = f"cmd_{uuid.uuid4().hex[:12]}"
    command = {
        "id": command_id,
        "type": request.command_type,
        "params": request.params,
        "issued_by": current_user.username,
        "issued_at": datetime.now().isoformat()
    }
    
    # Send command in background
    background_tasks.add_task(send_command_to_agent, request.agent_id, command)
    
    return CommandResponse(
        command_id=command_id,
        agent_id=request.agent_id,
        command_type=request.command_type,
        status="pending",
        created_at=datetime.now().isoformat()
    )


@router.get("/logs/{agent_id}")
async def get_agent_logs(
    agent_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get command logs for an agent.
    """
    # In production, fetch from database
    # For now, return from in-memory store
    if agent_id not in connected_agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    logs = connected_agents[agent_id].get("command_logs", [])
    return {"agent_id": agent_id, "logs": logs[-limit:]}


@router.post("/command/full-optimize/{agent_id}")
async def full_optimize(
    agent_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin)
):
    """
    Shortcut to send a full_optimize command.
    """
    request = CommandRequest(
        agent_id=agent_id,
        command_type="full_optimize",
        params={}
    )
    return await send_command(request, background_tasks, current_user)


@router.post("/command/uninstall/{agent_id}")
async def uninstall_agent(
    agent_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin)
):
    """
    Uninstall/self-destruct an agent.
    """
    request = CommandRequest(
        agent_id=agent_id,
        command_type="self_destruct",
        params={"confirm": True}
    )
    return await send_command(request, background_tasks, current_user)
