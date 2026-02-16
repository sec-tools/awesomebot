import subprocess
import re
from typing import List, Dict, Any
from .base import Tool, ToolResult


class DebugTool(Tool):
    """Debug tool for executing shell commands (admin-only)"""
    
    def _get_description(self) -> str:
        return "Execute shell commands for debugging (admin-only)"
    
    def _get_patterns(self) -> List[str]:
        return [
            r'^debug:\s*(.+)',  # "debug: ls", "debug: whoami", etc.
        ]
    
    async def execute(self, user_message: str, context: Dict[str, Any]) -> ToolResult:
        """Execute a shell command"""
        # Extract command from "debug: <command>" format
        match = re.search(r'debug:\s*(.+)', user_message.strip(), re.IGNORECASE)
        if not match:
            return ToolResult(
                success=False,
                output="",
                error="Invalid debug command format. Use: debug: <command>",
                metadata={"tool": "debug"}
            )
        
        command = match.group(1).strip()
        
        try:
            # Execute the shell command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Combine stdout and stderr
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                if output:
                    output += "\n"
                output += f"STDERR: {result.stderr}"
            
            if not output:
                output = f"Command executed successfully (exit code: {result.returncode})"
            
            return ToolResult(
                success=True,
                output=output,
                error=None,
                metadata={
                    "tool": "debug",
                    "command": command,
                    "exit_code": result.returncode
                }
            )
            
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output="",
                error="Command timed out after 30 seconds",
                metadata={"tool": "debug", "command": command}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Error executing command: {str(e)}",
                metadata={"tool": "debug", "command": command}
            )
