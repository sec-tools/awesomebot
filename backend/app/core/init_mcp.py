"""Initialize built-in MCP servers"""
import os
import json
import uuid
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.mcp_server import MCPServer
from app.models.user import User
from app.services.mcp_client import mcp_manager


async def init_builtin_mcp_servers(db: AsyncSession) -> None:
    """
    Initialize built-in MCP servers.
    
    Creates the default 'Awesome MCP Server' that provides weather,
    datetime, and system update checking tools out of the box.
    The server is assigned to the admin user.
    """
    
    # Path to the built-in MCP server
    backend_root = Path(__file__).parent.parent.parent
    mcp_server_path = backend_root / "awesome_mcp_server.py"
    
    if not mcp_server_path.exists():
        print(f"⚠️  Built-in MCP server not found: {mcp_server_path}")
        return
    
    # Make sure the script is executable
    try:
        os.chmod(mcp_server_path, 0o755)
    except Exception as e:
        print(f"⚠️  Failed to make MCP server executable: {e}")
    
    # Check if the built-in server already exists in the database
    result = await db.execute(
        select(MCPServer).where(MCPServer.name == "Awesome MCP Server")
    )
    existing = result.scalars().first()
    
    if existing:
        print("ℹ️  Built-in MCP server already exists in database")
        
        # Ensure it's running if enabled
        if existing.enabled and existing.id not in mcp_manager.clients:
            try:
                success = await mcp_manager.add_server(
                    existing.id,
                    existing.command,
                    json.loads(existing.args) if existing.args else [],
                    json.loads(existing.env) if existing.env else {}
                )
                
                if success:
                    print(f"✅ Built-in MCP server started: {existing.name}")
                else:
                    print(f"⚠️  Failed to start built-in MCP server: {existing.name}")
            except Exception as e:
                print(f"⚠️  Error starting built-in MCP server: {e}")
        return
    
    # Find the admin user to assign the built-in server to
    admin_result = await db.execute(
        select(User).where(User.username == "admin")
    )
    admin_user = admin_result.scalar_one_or_none()
    
    if not admin_user:
        print("⚠️  Admin user not found, skipping built-in MCP server initialization")
        return
    
    # Create the built-in MCP server entry
    server_id = str(uuid.uuid4())
    server = MCPServer(
        id=server_id,
        name="Awesome MCP Server",
        command="python3",
        args=json.dumps([str(mcp_server_path)]),
        env=json.dumps({}),
        enabled=True,
        user_id=admin_user.id
    )
    
    db.add(server)
    await db.flush()
    
    # Start the MCP server
    try:
        success = await mcp_manager.add_server(
            server_id,
            "python3",
            [str(mcp_server_path)],
            {}
        )
        
        if success:
            print(f"✅ Built-in MCP server initialized: {server.name}")
        else:
            print(f"⚠️  Built-in MCP server created but failed to start")
    except Exception as e:
        print(f"⚠️  Error starting built-in MCP server: {e}")
    
    await db.commit()
