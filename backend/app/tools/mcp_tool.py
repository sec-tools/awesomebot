"""MCP Tool - integrates MCP servers with the tool system"""
import re
import json
from typing import Dict, Any, List
from app.tools.base import Tool, ToolResult
from app.services.mcp_client import mcp_manager


class MCPTool(Tool):
    """Tool for using MCP (Model Context Protocol) servers"""
    
    def __init__(self):
        super().__init__()
        self.mcp_manager = mcp_manager
    
    def _get_description(self) -> str:
        return "Uses MCP (Model Context Protocol) servers to access external tools and data sources"
    
    def _get_patterns(self) -> List[str]:
        return [
            r'\buse\s+mcp\b',
            r'\bmcp\s+tool\b',
            r'\bmcp\s+server\b',
            # Will be dynamically matched based on available MCP tools
        ]
    
    async def matches_mcp_tool(self, message: str) -> tuple[bool, str, str, Dict]:
        """Check if message matches any MCP tool and return tool details"""
        # Get all available MCP tools
        all_tools = await self.mcp_manager.get_all_tools()
        
        message_lower = message.lower().strip()
        
        # Pattern-based matching for common natural language queries
        # Weather queries
        weather_patterns = [
            r'\bweather\s+(?:for|in|at)\s+([a-zA-Z\s]+?)(?:\?|$|\.)',
            r'\bwhat(?:\'s| is)\s+the\s+weather\s+(?:in|at|for)\s+([a-zA-Z\s]+?)(?:\?|$|\.)',
            r'\bhow(?:\'s| is)\s+the\s+weather\s+(?:in|at|for)\s+([a-zA-Z\s]+?)(?:\?|$|\.)',
            r'\bget\s+weather\s+(?:for|in)\s+([a-zA-Z\s]+?)(?:\?|$|\.)',
        ]
        
        for pattern in weather_patterns:
            match = re.search(pattern, message_lower)
            if match:
                # Find the get_weather tool
                for tool in all_tools:
                    if tool.get("name") == "get_weather":
                        return True, tool["server_id"], tool["name"], tool.get("inputSchema", {}), {"city": match.group(1).strip()}
        
        # Date/Time queries
        datetime_patterns = [
            r'\bwhat\s+(?:time\s+is\s+it|is\s+the\s+time|\'s\s+the\s+time)',
            r'\bwhat\s+(?:date\s+is\s+it|is\s+the\s+date|is\s+today)',
            r'\bwhat\s+day\s+is\s+(?:it|today)',
            r'\bget\s+(?:date|time|datetime)',
            r'\bcurrent\s+(?:date|time|datetime)',
            r'\btoday(?:\'s| is)\s+date',
        ]
        
        for pattern in datetime_patterns:
            if re.search(pattern, message_lower):
                # Find the get_datetime tool
                for tool in all_tools:
                    if tool.get("name") == "get_datetime":
                        return True, tool["server_id"], tool["name"], tool.get("inputSchema", {}), {}
        
        # System update queries
        update_patterns = [
            r'\bcheck\s+updates?\s+(?:for|on)\s+([a-zA-Z0-9\-_\.\$]+)',
            r'\bsystem\s+updates?',
            r'\bcheck\s+(?:for\s+)?updates?(?:\s+on)?(?:\s+system)?$',
            r'\bpackage\s+updates?',
        ]
        
        for pattern in update_patterns:
            match = re.search(pattern, message_lower)
            if match:
                # Find the check_updates tool
                for tool in all_tools:
                    if tool.get("name") == "check_updates":
                        # Use ORIGINAL message (not lowercased) to preserve case of env vars like $PATH
                        original_match = re.search(pattern, message, re.IGNORECASE)
                        package = original_match.group(1).strip() if original_match and original_match.lastindex else ""
                        return True, tool["server_id"], tool["name"], tool.get("inputSchema", {}), {"package": package}
        
        # Fallback: Check each MCP tool's name and description
        for tool in all_tools:
            tool_name = tool.get("name", "").lower()
            tool_desc = tool.get("description", "").lower()
            
            # Check if tool name is mentioned
            if tool_name in message_lower:
                return True, tool["server_id"], tool["name"], tool.get("inputSchema", {}), {}
            
            # Check if description keywords match
            desc_words = set(tool_desc.split())
            message_words = set(message_lower.split())
            common_words = desc_words & message_words
            
            if len(common_words) >= 2:  # At least 2 common keywords
                return True, tool["server_id"], tool["name"], tool.get("inputSchema", {}), {}
        
        return False, None, None, None, None
    
    def matches(self, message: str) -> bool:
        """Check if this tool matches the message"""
        message_lower = message.lower().strip()
        
        print(f"🔍 MCPTool.matches() checking: '{message_lower}'")
        
        # Check base patterns
        for pattern in self.patterns:
            if re.search(pattern, message_lower):
                print(f"✅ MCPTool matched base pattern: {pattern}")
                return True
        
        # Check for weather patterns
        weather_patterns = [
            r'\bweather\s+(?:for|in|at)\s+',
            r'\bwhat(?:\'s| is)\s+the\s+weather',
            r'\bhow(?:\'s| is)\s+the\s+weather',
            r'\bget\s+weather\s+',
        ]
        
        for pattern in weather_patterns:
            if re.search(pattern, message_lower):
                print(f"✅ MCPTool matched weather pattern: {pattern}")
                return True
        
        # Check for date/time patterns
        datetime_patterns = [
            r'\bwhat\s+(?:time\s+is\s+it|is\s+the\s+time|\'s\s+the\s+time)',
            r'\bwhat\s+(?:date\s+is\s+it|is\s+the\s+date|is\s+today)',
            r'\bwhat\s+day\s+is\s+(?:it|today)',
            r'\bget\s+(?:date|time|datetime)',
            r'\bcurrent\s+(?:date|time|datetime)',
            r'\btoday(?:\'s| is)\s+date',
        ]
        
        for pattern in datetime_patterns:
            if re.search(pattern, message_lower):
                print(f"✅ MCPTool matched datetime pattern: {pattern}")
                return True
        
        # Check for system update patterns
        update_patterns = [
            r'\bcheck\s+updates?',
            r'\bsystem\s+updates?',
            r'\bpackage\s+updates?',
        ]
        
        for pattern in update_patterns:
            if re.search(pattern, message_lower):
                print(f"✅ MCPTool matched update pattern: {pattern}")
                return True
        
        print(f"❌ MCPTool no match for: '{message_lower}'")
        return False
    
    async def execute(self, user_message: str, context: Dict[str, Any]) -> ToolResult:
        """Execute using MCP server"""
        
        # Check if message matches any MCP tool
        match_result = await self.matches_mcp_tool(user_message)
        
        if len(match_result) == 5:
            matches, server_id, tool_name, input_schema, extracted_args = match_result
        else:
            # Old format for compatibility
            matches, server_id, tool_name, input_schema = match_result
            extracted_args = {}
        
        if not matches:
            return ToolResult(
                success=False,
                output="",
                error="No matching MCP tool found. Please configure MCP servers first.",
                generated_code=None,
                metadata={"tool": "mcp"}
            )
        
        # Use extracted arguments from pattern matching, or fall back to extraction
        if extracted_args:
            arguments = extracted_args
        else:
            arguments = self._extract_arguments(user_message, input_schema)
        
        # Call the MCP tool
        try:
            result = await self.mcp_manager.call_tool(server_id, tool_name, arguments)
            
            # Format the result
            if "content" in result:
                output = self._format_mcp_result(result["content"])
            else:
                output = json.dumps(result, indent=2)
            
            # For MCP tools, we want the output to be displayed directly without AI reinterpretation
            # Mark the output as final to prevent AI from adding commentary
            final_output = output
            
            # Don't generate verbose code for MCP tools - keep it clean
            code = None
            
            return ToolResult(
                success=True,
                output=final_output,
                error=None,
                generated_code=code,
                metadata={
                    "tool": "mcp",
                    "server_id": server_id,
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "display_directly": True  # Signal to display output directly
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"MCP tool error: {str(e)}",
                generated_code=None,
                metadata={"tool": "mcp", "server_id": server_id, "tool_name": tool_name}
            )
    
    def _extract_arguments(self, message: str, input_schema: Dict) -> Dict[str, Any]:
        """Extract arguments from message based on input schema"""
        # Simplified argument extraction
        # In a production system, this would use LLM to extract structured data
        
        arguments = {}
        
        if not input_schema or "properties" not in input_schema:
            return arguments
        
        properties = input_schema.get("properties", {})
        message_lower = message.lower()
        
        # Enhanced extraction for common patterns
        for prop_name, prop_info in properties.items():
            # Special handling for "city" parameter (weather queries)
            if prop_name == "city":
                # Try various patterns
                city_patterns = [
                    r'weather\s+(?:for|in|at)\s+([a-zA-Z\s]+?)(?:\?|$|\.|,)',
                    r'in\s+([A-Z][a-zA-Z\s]+?)(?:\?|$|\.|,)',
                ]
                for pattern in city_patterns:
                    match = re.search(pattern, message, re.IGNORECASE)
                    if match:
                        arguments[prop_name] = match.group(1).strip()
                        break
            
            # Special handling for "package" parameter (update queries)
            elif prop_name == "package":
                package_pattern = r'(?:updates?\s+(?:for|on)\s+|package\s+)([a-zA-Z0-9\-_\.\$]+)'
                match = re.search(package_pattern, message_lower)
                if match:
                    arguments[prop_name] = match.group(1).strip()
            
            # Generic keyword extraction
            else:
                pattern = rf'{prop_name}[:\s]+([^\s,\.]+)'
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    arguments[prop_name] = match.group(1)
        
        return arguments
    
    def _format_mcp_result(self, content: List[Dict]) -> str:
        """Format MCP result content"""
        output_parts = []
        
        for item in content:
            if item.get("type") == "text":
                output_parts.append(item.get("text", ""))
            elif item.get("type") == "resource":
                uri = item.get("resource", {}).get("uri", "")
                text = item.get("resource", {}).get("text", "")
                output_parts.append(f"Resource: {uri}\n{text}")
            else:
                output_parts.append(json.dumps(item, indent=2))
        
        return "\n\n".join(output_parts)


