"""Tool registry for managing available tools"""
from typing import List, Optional, Dict, Any
from app.tools.base import Tool, ToolResult
from app.tools.math_tool import MathTool
from app.tools.web_search_tool import WebSearchTool
from app.tools.document_search_tool import DocumentSearchTool
from app.tools.code_executor_tool import CodeExecutorTool
from app.tools.file_analysis_tool import FileAnalysisTool
from app.tools.mcp_tool import MCPTool
from app.tools.read_file_tool import ReadFileTool
from app.tools.write_file_tool import WriteFileTool
from app.tools.curl_tool import CurlTool
from app.tools.conversation_memory_tool import ConversationMemoryTool
from app.tools.product_search_tool import ProductSearchTool
from app.tools.debug_tool import DebugTool
from app.tools.webpage_summary_tool import WebpageSummaryTool


class ToolRegistry:
    """Registry for managing and selecting tools"""
    
    def __init__(self):
        self.tools: List[Tool] = []
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register all default tools"""
        # Order matters! More specific tools first
        self.register_tool(MCPTool())  # MCP servers (check first for external tools)
        self.register_tool(ConversationMemoryTool())  # Conversation memory search
        self.register_tool(DebugTool())  # Debug commands (admin-only)
        self.register_tool(WebpageSummaryTool())  # Webpage summary tool
        self.register_tool(ProductSearchTool())  # AwesomeGear product catalog
        self.register_tool(CurlTool())  # HTTP requests (before code executor)
        self.register_tool(ReadFileTool())  # File reading
        self.register_tool(WriteFileTool())  # File writing
        self.register_tool(CodeExecutorTool())  # Check for explicit code execution
        self.register_tool(DocumentSearchTool())  # Document search
        self.register_tool(WebSearchTool())  # Web search
        self.register_tool(FileAnalysisTool())  # File analysis
        self.register_tool(MathTool())  # Math (most common, check last)
    
    def register_tool(self, tool: Tool):
        """Register a new tool"""
        self.tools.append(tool)
    
    def get_tool(self, message: str) -> Optional[Tool]:
        """Get the most appropriate tool for a message"""
        for tool in self.tools:
            if tool.matches(message):
                return tool
        return None
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get information about all registered tools"""
        return [tool.get_info() for tool in self.tools]
    
    async def execute_with_tool(self, message: str, context: Dict[str, Any]) -> Optional[ToolResult]:
        """Find and execute appropriate tool"""
        tool = self.get_tool(message)
        
        if tool:
            return await tool.execute(message, context)
        
        return None

