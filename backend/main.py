"""
AwesomeBot - Optimized AI Chat Platform
Main FastAPI application
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import init_db, get_db
from app.api import chat, conversations, files, code, auth, admin, agent, mcp, guardrails, awesomegear
from app.services import OllamaService
from app.core.auth import create_admin_user
from app.core.init_settings import init_system_settings
from app.core.init_mcp import init_builtin_mcp_servers
# Import all models to ensure they are registered with Base
from app.models import Conversation, Message, Document, User, SystemSettings
from app.models.mcp_server import MCPServer
from app.models.guardrails import GuardRail
from app.models.products import Product

# Create data directories
os.makedirs("./data", exist_ok=True)
os.makedirs("./data/uploads", exist_ok=True)
os.makedirs("./data/chroma_db", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("🚀 Starting AwesomeBot...")
    
    # Initialize database
    await init_db()
    print("✅ Database initialized")
    
    # Initialize system settings, create admin user, seed products, and setup built-in MCP servers
    from app.core.seed_products import seed_products
    async for db in get_db():
        await init_system_settings(db)
        await create_admin_user(db)
        await seed_products(db)
        await init_builtin_mcp_servers(db)
        break
    
    # Check Ollama connection with retry logic
    ollama = OllamaService()
    max_retries = 30
    retry_delay = 2
    
    for attempt in range(max_retries):
        if await ollama.check_health():
            print(f"✅ Ollama connected ({settings.DEFAULT_MODEL})")
            break
        elif attempt < max_retries - 1:
            print(f"⏳ Waiting for Ollama... (attempt {attempt + 1}/{max_retries})")
            import asyncio
            await asyncio.sleep(retry_delay)
        else:
            print("⚠️  Ollama not available after max retries (service will continue)")
    
    print(f"🎉 AwesomeBot ready at http://0.0.0.0:8000")
    
    yield
    
    # Shutdown
    await ollama.close()
    print("👋 AwesomeBot shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="AwesomeBot API",
    description="Optimized AI Chat Platform with RAG and Code Execution",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(agent.router, prefix="/api/agent", tags=["agent"])
app.include_router(mcp.router, prefix="/api/mcp", tags=["mcp"])
app.include_router(guardrails.router, prefix="/api/guardrails", tags=["guardrails"])
app.include_router(awesomegear.router, prefix="/api/awesomegear", tags=["awesomegear"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["conversations"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(code.router, prefix="/api/code", tags=["code"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "AwesomeBot",
        "version": "2.0.0",
        "status": "running",
        "features": [
            "Fast AI chat with Qwen models",
            "Memory-efficient RAG",
            "Secure code execution",
            "Conversation management",
            "Document processing"
        ],
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint - uses singleton service."""
    from app.services.ollama_service import get_ollama_service
    
    ollama = get_ollama_service()
    ollama_status = await ollama.check_health()
    
    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "ollama": "connected" if ollama_status else "disconnected",
            "database": "connected",
            "model": settings.DEFAULT_MODEL
        }
    }


if __name__ == "__main__":
    import uvicorn
    import os
    
    # Determine environment
    is_production = os.getenv("ENVIRONMENT", "development") == "production"
    
    if is_production:
        # Production settings - optimized for 24/7 operation
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            workers=1,                    # Single worker (SQLite limitation)
            limit_concurrency=100,        # Max concurrent connections
            timeout_keep_alive=300,       # 5 minute keep-alive (matches model keep-alive)
            timeout_graceful_shutdown=30, # Graceful shutdown timeout
            log_level="warning",          # Reduce log verbosity
            access_log=False,             # Disable access logging for performance
        )
    else:
        # Development settings
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
