"""MCP Server management API endpoints"""
import uuid
import json
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.models.mcp_server import MCPServer
from app.core.auth import get_current_user
from app.services.mcp_client import mcp_manager

router = APIRouter()


@router.get("/debug/status")
async def debug_mcp_status(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Debug endpoint to check MCP manager status"""
    tools = await mcp_manager.get_all_tools()
    return {
        "clients": len(mcp_manager.clients),
        "client_ids": list(mcp_manager.clients.keys()),
        "tools_cache_servers": len(mcp_manager.tools_cache),
        "total_tools": len(tools),
        "tools": [{"name": t.get("name"), "description": t.get("description")} for t in tools]
    }


class MCPServerCreate(BaseModel):
    """MCP Server creation model"""
    name: str
    command: str
    args: List[str] = []
    env: dict = {}


class MCPServerResponse(BaseModel):
    """MCP Server response model"""
    id: str
    name: str
    command: str
    args: List[str]
    env: dict
    enabled: bool
    created_at: datetime


@router.get("/servers")
async def list_mcp_servers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all MCP servers for current user"""
    
    result = await db.execute(
        select(MCPServer).where(MCPServer.user_id == current_user.id)
    )
    servers = result.scalars().all()
    
    return {
        "servers": [
            {
                "id": s.id,
                "name": s.name,
                "command": s.command,
                "args": s.get_args(),
                "env": s.get_env(),
                "enabled": s.enabled,
                "created_at": s.created_at
            }
            for s in servers
        ]
    }


@router.post("/servers")
async def create_mcp_server(
    server_data: MCPServerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create and start a new MCP server"""
    
    import json
    
    server = MCPServer(
        id=str(uuid.uuid4()),
        name=server_data.name,
        command=server_data.command,
        args=json.dumps(server_data.args),
        env=json.dumps(server_data.env),
        enabled=True,
        user_id=current_user.id
    )
    
    # Try to start the MCP server
    success = await mcp_manager.add_server(
        server.id,
        server.command,
        server_data.args,
        server_data.env
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to start MCP server")
    
    db.add(server)
    await db.commit()
    await db.refresh(server)
    
    return {
        "id": server.id,
        "name": server.name,
        "command": server.command,
        "args": server.get_args(),
        "env": server.get_env(),
        "enabled": server.enabled
    }


@router.delete("/servers/{server_id}")
async def delete_mcp_server(
    server_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an MCP server"""
    
    result = await db.execute(
        select(MCPServer).where(
            MCPServer.id == server_id,
            MCPServer.user_id == current_user.id
        )
    )
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    # Stop the MCP server
    await mcp_manager.remove_server(server_id)
    
    await db.delete(server)
    await db.commit()
    
    return {"message": "MCP server deleted"}


@router.get("/servers/{server_id}/tools")
async def get_mcp_server_tools(
    server_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available tools from an MCP server"""
    
    result = await db.execute(
        select(MCPServer).where(
            MCPServer.id == server_id,
            MCPServer.user_id == current_user.id
        )
    )
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    # Get tools from MCP manager
    all_tools = await mcp_manager.get_all_tools()
    server_tools = [t for t in all_tools if t.get("server_id") == server_id]
    
    return {"tools": server_tools}


@router.get("/tools")
async def list_all_mcp_tools(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all available MCP tools from all servers"""
    
    tools = await mcp_manager.get_all_tools()
    
    # Enrich tools with server names from database
    result = await db.execute(select(MCPServer))
    servers = {s.id: s.name for s in result.scalars().all()}
    
    for tool in tools:
        server_id = tool.get("server_id")
        if server_id in servers:
            server_name = servers[server_id]
            # Rename built-in server for display
            if server_name == "Awesome MCP Server":
                server_name = "Awesome Server (Built-in)"
            tool["server_name"] = server_name
        else:
            tool["server_name"] = "Unknown Server"
    
    return {"tools": tools}


@router.post("/servers/{server_id}/refresh")
async def refresh_mcp_server(
    server_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Refresh tools cache for an MCP server"""
    
    result = await db.execute(
        select(MCPServer).where(
            MCPServer.id == server_id,
            MCPServer.user_id == current_user.id
        )
    )
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    await mcp_manager.refresh_tools(server_id)
    
    return {"message": "Tools cache refreshed"}


@router.patch("/servers/{server_id}/toggle")
async def toggle_mcp_server(
    server_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Enable/disable an MCP server"""
    
    result = await db.execute(
        select(MCPServer).where(
            MCPServer.id == server_id,
            MCPServer.user_id == current_user.id
        )
    )
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    
    server.enabled = not server.enabled
    server.updated_at = datetime.utcnow()
    
    if server.enabled:
        # Start the server
        success = await mcp_manager.add_server(
            server.id,
            server.command,
            server.get_args(),
            server.get_env()
        )
        if not success:
            raise HTTPException(status_code=400, detail="Failed to start MCP server")
    else:
        # Stop the server
        await mcp_manager.remove_server(server_id)
    
    await db.commit()
    
    return {"enabled": server.enabled}


@router.post("/servers/upload")
async def upload_mcp_config(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload and register MCP server configuration from a JSON file.
    
    Supports multiple formats:
    1. Single server object: {"name": "...", "command": "...", "args": [...], "env": {...}}
    2. Multiple servers array: [{"name": "...", ...}, {"name": "...", ...}]
    3. Claude Desktop format: {"mcpServers": {"server-name": {"command": "...", "args": [...], "env": {...}}}}
    """
    
    # Validate file type
    if not file.filename.endswith(('.json', '.txt')):
        raise HTTPException(
            status_code=400,
            detail="Only JSON files are supported (.json or .txt)"
        )
    
    try:
        # Read and parse file
        content = await file.read()
        config = json.loads(content.decode('utf-8'))
        
        servers_to_create = []
        
        # Parse different config formats
        if isinstance(config, dict):
            # Check for Claude Desktop format
            if "mcpServers" in config:
                # Claude Desktop format: {"mcpServers": {"name": {"command": "...", ...}}}
                for name, server_config in config["mcpServers"].items():
                    servers_to_create.append({
                        "name": name,
                        "command": server_config.get("command", ""),
                        "args": server_config.get("args", []),
                        "env": server_config.get("env", {})
                    })
            # Check for single server object
            elif "command" in config:
                servers_to_create.append({
                    "name": config.get("name", "Uploaded Server"),
                    "command": config.get("command", ""),
                    "args": config.get("args", []),
                    "env": config.get("env", {})
                })
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid config format. Expected 'command' field or 'mcpServers' object."
                )
        elif isinstance(config, list):
            # Array of server objects
            for server_config in config:
                if "command" not in server_config:
                    continue
                servers_to_create.append({
                    "name": server_config.get("name", "Uploaded Server"),
                    "command": server_config.get("command", ""),
                    "args": server_config.get("args", []),
                    "env": server_config.get("env", {})
                })
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid config format. Expected JSON object or array."
            )
        
        if not servers_to_create:
            raise HTTPException(
                status_code=400,
                detail="No valid MCP servers found in the uploaded file."
            )
        
        # Create servers
        created_servers = []
        failed_servers = []
        
        for server_data in servers_to_create:
            try:
                server = MCPServer(
                    id=str(uuid.uuid4()),
                    name=server_data["name"],
                    command=server_data["command"],
                    args=json.dumps(server_data["args"]),
                    env=json.dumps(server_data["env"]),
                    enabled=True,
                    user_id=current_user.id
                )
                
                # Try to start the MCP server
                success = await mcp_manager.add_server(
                    server.id,
                    server.command,
                    server_data["args"],
                    server_data["env"]
                )
                
                if success:
                    db.add(server)
                    await db.commit()
                    await db.refresh(server)
                    
                    created_servers.append({
                        "id": server.id,
                        "name": server.name,
                        "command": server.command,
                        "args": server.get_args(),
                        "env": server.get_env(),
                        "enabled": server.enabled
                    })
                else:
                    failed_servers.append({
                        "name": server_data["name"],
                        "error": "Failed to start server"
                    })
            except Exception as e:
                failed_servers.append({
                    "name": server_data.get("name", "Unknown"),
                    "error": str(e)
                })
        
        return {
            "message": f"Upload complete: {len(created_servers)} created, {len(failed_servers)} failed",
            "created": created_servers,
            "failed": failed_servers
        }
        
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON format in uploaded file"
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error processing file: {str(e)}"
        )


