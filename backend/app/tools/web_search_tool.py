"""Web search tool"""
import re
from typing import Dict, Any, List
from app.tools.base import Tool, ToolResult
from app.services.code_executor import CodeExecutor


class WebSearchTool(Tool):
    """Tool for searching the web"""
    
    def __init__(self):
        super().__init__()
        self.code_executor = CodeExecutor()
    
    def _get_description(self) -> str:
        return "Searches the web using DuckDuckGo to find information"
    
    def _get_patterns(self) -> List[str]:
        return [
            r'\bsearch\s+(the\s+)?web\b',
            r'\bsearch\s+online\b',
            r'\bsearch\s+internet\b',
            r'\blook\s+up\b',
            r'\bfind\s+information\b',
            r'\bwhat\s+is\s+(the\s+)?(current|latest)\b',
            r'\bwho\s+is\b',
            r'\bwhen\s+(did|was|is)\b',
            r'\bwhere\s+(is|was)\b',
        ]
    
    def _generate_code(self, query: str) -> str:
        """Generate Python code for web search"""
        # Extract the actual search query
        clean_query = re.sub(r'\b(search|the|web|online|internet|look\s+up|find)\b', '', query, flags=re.IGNORECASE)
        clean_query = clean_query.strip()
        
        if not clean_query:
            clean_query = query
        
        code = f"""# Web Search: {clean_query}
import subprocess
import json
import urllib.parse

try:
    # Use DuckDuckGo Instant Answer API via curl (urllib blocked by DDG)
    query = {repr(clean_query)}
    url = f"https://api.duckduckgo.com/?q={{urllib.parse.quote(query)}}&format=json"
    
    # Use curl which works reliably with DuckDuckGo
    result = subprocess.run(
        ['curl', '-s', '-H', 'User-Agent: Mozilla/5.0', url],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode == 0 and result.stdout:
        data = json.loads(result.stdout)
        
        # Extract relevant information
        results = []
        
        # Abstract/summary
        if data.get('Abstract'):
            results.append(f"Summary: {{data['Abstract']}}")
        
        # Related topics
        if data.get('RelatedTopics'):
            results.append("\\nRelated Information:")
            for topic in data['RelatedTopics'][:3]:
                if isinstance(topic, dict) and 'Text' in topic:
                    results.append(f"- {{topic['Text']}}")
        
        # Definition
        if data.get('Definition'):
            results.append(f"\\nDefinition: {{data['Definition']}}")
        
        if results:
            print("\\n".join(results))
        else:
            print(f"No detailed results found for: {{query}}")
            print(f"\\nTry searching: https://duckduckgo.com/?q={{urllib.parse.quote(query)}}")
    else:
        print(f"Search failed. Try: https://duckduckgo.com/?q={{urllib.parse.quote(query)}}")
            
except Exception as e:
    print(f"Search error: {{str(e)}}")
    print(f"Manual search: https://duckduckgo.com/?q={{urllib.parse.quote(query)}}")
"""
        return code
    
    async def execute(self, user_message: str, context: Dict[str, Any]) -> ToolResult:
        """Execute web search"""
        
        code = self._generate_code(user_message)
        
        # Execute the search code
        execution_result = await self.code_executor.execute_python(code)
        
        return ToolResult(
            success=execution_result.get("success", False),
            output=execution_result.get("output", ""),
            error=execution_result.get("error", ""),
            generated_code=code,
            metadata={"tool": "web_search", "query": user_message}
        )


