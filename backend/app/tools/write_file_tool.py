"""Write file tool"""
import re
import os
from typing import Dict, Any, List, Optional, Tuple
from app.tools.base import Tool, ToolResult


class WriteFileTool(Tool):
    """Tool for writing content to files"""
    
    def _get_description(self) -> str:
        return "Writes content to a file"
    
    def _get_patterns(self) -> List[str]:
        return [
            r'\bwrite\s+(?:to\s+)?(?:the\s+)?file',
            r'\bsave\s+(?:to\s+)?(?:the\s+)?file',
            r'\bcreate\s+(?:a\s+)?file',
            r'\bwrite\s+.*\s+to\s+\S+',
            r'\bsave\s+.*\s+to\s+\S+',
            r'\bput\s+.*\s+(?:in|into)\s+(?:the\s+)?file',
        ]
    
    def _extract_file_and_content(self, message: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract file path and content from message"""
        
        filepath = None
        content = None
        
        # Look for file path in quotes
        quote_match = re.search(r'["\']([^"\']+\.\w+)["\']', message)
        if quote_match:
            filepath = quote_match.group(1)
        
        # Look for file path after keywords
        if not filepath:
            patterns = [
                r'(?:write|save|create)\s+(?:to\s+)?(?:the\s+)?(?:file\s+)?(?:at\s+)?([^\s,]+\.\w+)',
                r'(?:file\s+named|file\s+called)\s+([^\s,]+)',
                r'(?:in|to|into)\s+(?:the\s+)?file\s+([^\s,]+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    filepath = match.group(1).rstrip('.,!?')
                    break
        
        # Look for anything that looks like a file path
        if not filepath:
            path_match = re.search(r'([~./]?[\w/.-]+\.\w+)', message)
            if path_match:
                filepath = path_match.group(1)
        
        # Extract content from code blocks
        code_block_match = re.search(r'```(?:\w+)?\s*\n(.*?)```', message, re.DOTALL)
        if code_block_match:
            content = code_block_match.group(1).strip()
        
        # Extract content in quotes (if not already used for filepath)
        if not content:
            # Look for content after "with content" or similar
            content_patterns = [
                r'(?:with\s+)?(?:content|text|data):?\s*["\']([^"\']+)["\']',
                r'(?:write|save)\s+["\']([^"\']+)["\']',
            ]
            
            for pattern in content_patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match and match.group(1) != filepath:
                    content = match.group(1)
                    break
        
        # If still no content, try to extract everything after "write/save X"
        if not content and filepath:
            # Try to find content between quotes or after keywords
            after_match = re.search(rf'{re.escape(filepath)}.*?:\s*(.+)', message, re.IGNORECASE | re.DOTALL)
            if after_match:
                content = after_match.group(1).strip()
        
        return (filepath, content)
    
    async def execute(self, user_message: str, context: Dict[str, Any]) -> ToolResult:
        """Write content to file"""
        
        filepath, content = self._extract_file_and_content(user_message)
        
        if not filepath:
            return ToolResult(
                success=False,
                output="",
                error="Could not determine file path. Please specify where to write the file.",
                metadata={"tool": "write_file"}
            )
        
        if not content:
            return ToolResult(
                success=False,
                output="",
                error="No content provided to write. Please specify what to write to the file.",
                metadata={"tool": "write_file", "filepath": filepath}
            )
        
        # Expand ~ to home directory
        if filepath.startswith('~'):
            filepath = os.path.expanduser(filepath)
        
        # Convert relative paths to absolute (within working directory)
        if not os.path.isabs(filepath):
            # Use /app/data for safety (writable directory in container)
            base_dir = os.getenv('WRITABLE_DIR', '/app/data/user_files')
            os.makedirs(base_dir, exist_ok=True)
            filepath = os.path.join(base_dir, filepath)
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Write file contents
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Get file info
            file_size = os.path.getsize(filepath)
            line_count = content.count('\n') + 1
            
            output = f"✅ File written successfully!\n\n"
            output += f"Path: {filepath}\n"
            output += f"Size: {file_size} bytes\n"
            output += f"Lines: {line_count}\n"
            output += f"\nContent preview:\n{'='*60}\n"
            
            # Show preview of content
            preview = content[:500]
            if len(content) > 500:
                preview += f"\n... (truncated, total {len(content)} characters)"
            output += preview
            
            return ToolResult(
                success=True,
                output=output,
                error=None,
                metadata={
                    "tool": "write_file",
                    "filepath": filepath,
                    "size": file_size,
                    "lines": line_count
                }
            )
        
        except PermissionError:
            return ToolResult(
                success=False,
                output="",
                error=f"Permission denied: Cannot write to {filepath}",
                metadata={"tool": "write_file", "filepath": filepath}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Error writing file: {str(e)}",
                metadata={"tool": "write_file", "filepath": filepath}
            )


