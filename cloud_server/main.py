"""
Autonova RMM - Cloud Server Main Entry
FastAPI application with Socket.IO for real-time communication.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio
import uvicorn

# Use absolute imports instead of relative
from api.auth import router as auth_router
from api.commands import router as commands_router
from sockets.agent_socket import AgentNamespace
from database.models import init_db

# Allowed origins for CORS
ALLOWED_ORIGINS = [
    "https://autonova-rmm.netlify.app",
    "https://autonova-rmm.onrender.com",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "*"  # Allow all for WebSocket connections
]

# Create FastAPI app
app = FastAPI(
    title="Autonova RMM Server",
    description="Command & Control server for Autonova RMM agents",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create Socket.IO server with production settings
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25,
)

# Create ASGI app combining FastAPI and Socket.IO
socket_app = socketio.ASGIApp(sio, app)

# Register Socket.IO namespace
agent_ns = AgentNamespace('/agents', sio)
sio.register_namespace(agent_ns)

# Register API routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(commands_router, prefix="/api", tags=["Commands"])


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    await init_db()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "Autonova RMM Server",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    from sockets.agent_socket import connected_agents
    
    return {
        "status": "healthy",
        "connected_agents": len(connected_agents),
        "agents": list(connected_agents.keys())
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:socket_app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
