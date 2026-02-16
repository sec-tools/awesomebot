"""Tools package - Modular tool system for AwesomeBot"""
from app.tools.base import Tool, ToolResult
from app.tools.math_tool import MathTool
from app.tools.web_search_tool import WebSearchTool
from app.tools.document_search_tool import DocumentSearchTool
from app.tools.code_executor_tool import CodeExecutorTool
from app.tools.file_analysis_tool import FileAnalysisTool

__all__ = [
    'Tool',
    'ToolResult',
    'MathTool',
    'WebSearchTool',
    'DocumentSearchTool',
    'CodeExecutorTool',
    'FileAnalysisTool',
]


