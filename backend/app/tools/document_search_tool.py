"""Document search tool"""
import re
from typing import Dict, Any, List
from app.tools.base import Tool, ToolResult
from app.services.rag_service import RAGService


class DocumentSearchTool(Tool):
    """Tool for searching uploaded documents"""
    
    def __init__(self):
        super().__init__()
        self.rag_service = RAGService()
    
    def _get_description(self) -> str:
        return "Searches through uploaded documents using RAG (Retrieval-Augmented Generation)"
    
    def _get_patterns(self) -> List[str]:
        return [
            r'\bsearch\s+(the\s+)?document',
            r'\bsearch\s+(my\s+)?files',
            r'\bfind\s+in\s+(the\s+)?document',
            r'\blook\s+in\s+(the\s+)?document',
            r'\bwhat\s+does\s+(the\s+)?document\s+say',
            r'\bin\s+(my\s+)?uploaded\s+(files|documents)',
        ]
    
    async def execute(self, user_message: str, context: Dict[str, Any]) -> ToolResult:
        """Execute document search"""
        
        # Extract the actual search query
        clean_query = re.sub(
            r'\b(search|find|look|the|document|files|uploaded|in|my)\b',
            '',
            user_message,
            flags=re.IGNORECASE
        )
        clean_query = clean_query.strip()
        
        if not clean_query:
            clean_query = user_message
        
        try:
            # Use RAG service to search documents
            results = await self.rag_service.get_context(clean_query)
            
            if results:
                output = f"📄 Document Search Results for: '{clean_query}'\\n\\n"
                output += results
                
                return ToolResult(
                    success=True,
                    output=output,
                    error=None,
                    generated_code=None,  # RAG doesn't use code generation
                    metadata={
                        "tool": "document_search",
                        "query": clean_query,
                        "found_results": True
                    }
                )
            else:
                return ToolResult(
                    success=True,
                    output=f"No relevant information found in documents for: '{clean_query}'\\n\\nTip: Upload documents via the Files page first.",
                    error=None,
                    generated_code=None,
                    metadata={
                        "tool": "document_search",
                        "query": clean_query,
                        "found_results": False
                    }
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Document search error: {str(e)}",
                generated_code=None,
                metadata={"tool": "document_search", "query": clean_query}
            )


