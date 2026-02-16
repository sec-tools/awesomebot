"""Read file tool"""
import re
import os
from typing import Dict, Any, List, Optional
from app.tools.base import Tool, ToolResult


class ReadFileTool(Tool):
    """Tool for reading file contents"""
    
    def _get_description(self) -> str:
        return "Reads contents from a file"
    
    def _get_patterns(self) -> List[str]:
        return [
            r'\bread\s+\S+\.\w+',  # "read filename.ext" - simple and direct!
            r'\bread\s+(the\s+)?(file|contents)',
            r'\bshow\s+(me\s+)?(the\s+)?(contents\s+of|file)',
            r'\bcat\s+\S+',
            r'\bopen\s+(the\s+)?file',
            r'\bwhat\'?s?\s+in\s+(the\s+)?file',
            r'\bview\s+(the\s+)?file',
            r'\bdisplay\s+(the\s+)?file',
        ]
    
    def _extract_filepath(self, message: str) -> Optional[str]:
        """Extract file path from message"""
        
        # Look for file path in quotes
        quote_match = re.search(r'["\']([^"\']+)["\']', message)
        if quote_match:
            return quote_match.group(1)
        
        # Look for file path after keywords
        patterns = [
            r'(?:read|open|cat|view|show|display)\s+(?:the\s+)?(?:file\s+)?(?:at\s+)?([^\s,]+)',
            r'(?:contents\s+of|file\s+at)\s+([^\s,]+)',
            r'in\s+(?:the\s+)?file\s+([^\s,]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                path = match.group(1)
                # Clean up any trailing punctuation
                path = path.rstrip('.,!?')
                return path
        
        # Look for anything that looks like a file path
        # Match common patterns: /path/to/file, ./file, ~/file, file.ext
        path_match = re.search(r'([~./]?[\w/.-]+\.\w+)', message)
        if path_match:
            return path_match.group(1)
        
        return None
    
    async def execute(self, user_message: str, context: Dict[str, Any]) -> ToolResult:
        """Read file contents"""
        
        filepath = self._extract_filepath(user_message)
        
        if not filepath:
            return ToolResult(
                success=False,
                output="",
                error="Could not determine which file to read. Please specify a file path.",
                metadata={"tool": "read_file"}
            )
        
        # Expand ~ to home directory
        if filepath.startswith('~'):
            filepath = os.path.expanduser(filepath)
        
        # Convert relative paths to absolute
        if not os.path.isabs(filepath):
            filepath = os.path.abspath(filepath)
        
        try:
            # Check if file exists
            if not os.path.exists(filepath):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"File not found: {filepath}",
                    metadata={"tool": "read_file", "filepath": filepath}
                )
            
            # Check if it's a file (not a directory)
            if not os.path.isfile(filepath):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Path is not a file: {filepath}",
                    metadata={"tool": "read_file", "filepath": filepath}
                )
            
            # Read file contents
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                contents = f.read()
            
            # Get file info
            file_size = os.path.getsize(filepath)
            line_count = contents.count('\n') + 1
            
            output = f"File: {filepath}\n"
            output += f"Size: {file_size} bytes\n"
            output += f"Lines: {line_count}\n"
            output += f"\n{'='*60}\n\n"
            output += contents
            
            # Limit output if too large
            if len(output) > 10000:
                output = output[:10000] + f"\n\n... (truncated, file is {len(contents)} characters)"
            
            return ToolResult(
                success=True,
                output=output,
                error=None,
                metadata={
                    "tool": "read_file",
                    "filepath": filepath,
                    "size": file_size,
                    "lines": line_count
                }
            )
        
        except PermissionError:
            return ToolResult(
                success=False,
                output="",
                error=f"Permission denied: Cannot read {filepath}",
                metadata={"tool": "read_file", "filepath": filepath}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Error reading file: {str(e)}",
                metadata={"tool": "read_file", "filepath": filepath}
            )


