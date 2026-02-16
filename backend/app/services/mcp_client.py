"""MCP (Model Context Protocol) client implementation"""
import asyncio
import json
import subprocess
from typing import Dict, List, Any, Optional
import uuid


class MCPClient:
    """Simple MCP client for communicating with MCP servers"""
    
    def __init__(self, command: str, args: List[str] = None, env: Dict[str, str] = None):
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.process = None
        self.request_id = 0
    
    async def start(self):
        """Start the MCP server process"""
        try:
            # Start subprocess with stdio communication
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**subprocess.os.environ.copy(), **self.env}
            )
            
            # Send initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "AwesomeBot",
                        "version": "2.0.0"
                    }
                }
            }
            
            response = await self._send_request(init_request)
            return response
            
        except Exception as e:
            raise Exception(f"Failed to start MCP server: {str(e)}")
    
    async def stop(self):
        """Stop the MCP server process"""
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except:
                pass
            self.process = None
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the MCP server"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list",
            "params": {}
        }
        
        response = await self._send_request(request)
        if response and "result" in response:
            return response["result"].get("tools", [])
        return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        response = await self._send_request(request)
        if response and "result" in response:
            return response["result"]
        return {"error": "No result from tool"}
    
    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources from the MCP server"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "resources/list",
            "params": {}
        }
        
        response = await self._send_request(request)
        if response and "result" in response:
            return response["result"].get("resources", [])
        return []
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource from the MCP server"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "resources/read",
            "params": {
                "uri": uri
            }
        }
        
        response = await self._send_request(request)
        if response and "result" in response:
            return response["result"]
        return {"error": "No result from resource"}
    
    async def _send_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a JSON-RPC request and get response"""
        if not self.process:
            raise Exception("MCP server not started")
        
        try:
            # Send request
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str.encode())
            await self.process.stdin.drain()
            
            # Read response
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=30.0
            )
            
            if response_line:
                response = json.loads(response_line.decode().strip())
                return response
            
            return None
            
        except asyncio.TimeoutError:
            return {"error": "Request timeout"}
        except Exception as e:
            return {"error": str(e)}
    
    def _next_id(self) -> int:
        """Get next request ID"""
        self.request_id += 1
        return self.request_id


class MCPManager:
    """Manages multiple MCP server connections"""
    
    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}
        self.tools_cache: Dict[str, List[Dict]] = {}
    
    async def add_server(self, server_id: str, command: str, args: List[str], env: Dict[str, str]):
        """Add and start an MCP server"""
        client = MCPClient(command, args, env)
        
        try:
            await client.start()
            self.clients[server_id] = client
            
            # Cache available tools
            tools = await client.list_tools()
            self.tools_cache[server_id] = tools
            
            return True
        except Exception as e:
            print(f"Failed to add MCP server {server_id}: {e}")
            return False
    
    async def remove_server(self, server_id: str):
        """Remove and stop an MCP server"""
        if server_id in self.clients:
            await self.clients[server_id].stop()
            del self.clients[server_id]
            if server_id in self.tools_cache:
                del self.tools_cache[server_id]
    
    async def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tools from all MCP servers"""
        all_tools = []
        for server_id, tools in self.tools_cache.items():
            for tool in tools:
                tool_copy = tool.copy()
                tool_copy["server_id"] = server_id
                all_tools.append(tool_copy)
        return all_tools
    
    async def call_tool(self, server_id: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on a specific MCP server"""
        if server_id not in self.clients:
            return {"error": f"MCP server {server_id} not found"}
        
        return await self.clients[server_id].call_tool(tool_name, arguments)
    
    async def refresh_tools(self, server_id: str):
        """Refresh tools cache for a server"""
        if server_id in self.clients:
            tools = await self.clients[server_id].list_tools()
            self.tools_cache[server_id] = tools
    
    async def shutdown_all(self):
        """Shutdown all MCP servers"""
        for client in self.clients.values():
            await client.stop()
        self.clients.clear()
        self.tools_cache.clear()


# Global MCP manager instance
mcp_manager = MCPManager()


