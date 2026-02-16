"""Base tool interface for modular tool system"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class ToolResult(BaseModel):
    """Result from tool execution"""
    success: bool
    output: str
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    generated_code: Optional[str] = None


class Tool(ABC):
    """Base class for all tools"""
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.description = self._get_description()
        self.patterns = self._get_patterns()
    
    @abstractmethod
    def _get_description(self) -> str:
        """Get tool description"""
        pass
    
    @abstractmethod
    def _get_patterns(self) -> List[str]:
        """Get regex patterns that trigger this tool"""
        pass
    
    @abstractmethod
    async def execute(self, user_message: str, context: Dict[str, Any]) -> ToolResult:
        """Execute the tool"""
        pass
    
    def matches(self, message: str) -> bool:
        """Check if this tool matches the message"""
        import re
        message_lower = message.lower()
        
        for pattern in self.patterns:
            if re.search(pattern, message_lower):
                return True
        
        return False
    
    def get_info(self) -> Dict[str, Any]:
        """Get tool information"""
        return {
            "name": self.name,
            "description": self.description,
            "patterns": self.patterns
        }


