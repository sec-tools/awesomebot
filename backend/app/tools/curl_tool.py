"""Curl tool for making HTTP requests"""
import re
import asyncio
from typing import Dict, Any, List, Optional
from app.tools.base import Tool, ToolResult


class CurlTool(Tool):
    """Tool for executing curl commands"""
    
    def _get_description(self) -> str:
        return "Executes curl commands to make HTTP requests"
    
    def _get_patterns(self) -> List[str]:
        return [
            r'\bcurl\s+',
            r'\bfetch\s+(?:from\s+)?https?://',
            r'\bget\s+(?:from\s+)?https?://',
            r'\bmake\s+(?:a\s+)?(?:http|https)\s+request',
            r'\bhttp\s+(?:get|post|put|delete)',
            r'\bapi\s+(?:call|request)',
        ]
    
    def _extract_curl_command(self, message: str) -> Optional[str]:
        """Extract curl command or construct from message"""
        
        # Look for explicit curl command
        curl_match = re.search(r'curl\s+([^\n]+)', message, re.IGNORECASE)
        if curl_match:
            return f"curl {curl_match.group(1).strip()}"
        
        # Look for URL
        url_match = re.search(r'https?://[^\s,\'"]+', message)
        if url_match:
            url = url_match.group(0)
            
            # Check for method specification
            method = "GET"
            method_match = re.search(r'\b(GET|POST|PUT|DELETE|PATCH)\b', message, re.IGNORECASE)
            if method_match:
                method = method_match.group(1).upper()
            
            # Check for headers
            headers = []
            header_matches = re.finditer(r'-H\s+["\']([^"\']+)["\']', message)
            for match in header_matches:
                headers.append(f'-H "{match.group(1)}"')
            
            # Check for data
            data = None
            data_match = re.search(r'(?:-d|--data)\s+["\']([^"\']+)["\']', message)
            if data_match:
                data = f'-d "{data_match.group(1)}"'
            
            # Construct curl command
            cmd = f"curl -X {method}"
            for header in headers:
                cmd += f" {header}"
            if data:
                cmd += f" {data}"
            cmd += f" {url}"
            
            return cmd
        
        return None
    
    async def execute(self, user_message: str, context: Dict[str, Any]) -> ToolResult:
        """Execute curl command"""
        
        curl_cmd = self._extract_curl_command(user_message)
        
        if not curl_cmd:
            return ToolResult(
                success=False,
                output="",
                error="Could not extract curl command or URL from message. Please provide a curl command or URL.",
                metadata={"tool": "curl"}
            )
        
        try:
            # Add timeout and follow redirects by default
            if '-L' not in curl_cmd:
                curl_cmd = curl_cmd.replace('curl', 'curl -L', 1)
            if '--max-time' not in curl_cmd and '-m' not in curl_cmd:
                curl_cmd += ' --max-time 5'
            
            # Add silent mode but show errors
            if '-s' not in curl_cmd:
                curl_cmd += ' -s'
            if '-S' not in curl_cmd:
                curl_cmd += ' -S'
            
            # Execute curl command
            process = await asyncio.create_subprocess_shell(
                curl_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={'PATH': '/usr/bin:/bin:/usr/local/bin'}
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=7.0  # Slightly more than curl's timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    success=False,
                    output="",
                    error="Request timed out after 7 seconds",
                    metadata={"tool": "curl", "command": curl_cmd}
                )
            
            stdout_str = stdout.decode('utf-8', errors='ignore')
            stderr_str = stderr.decode('utf-8', errors='ignore')
            
            # Curl returns 0 on success
            success = process.returncode == 0
            
            output = f"Command: {curl_cmd}\n"
            output += f"{'='*60}\n\n"
            
            if stdout_str:
                output += "Response:\n"
                # Limit output size
                if len(stdout_str) > 5000:
                    output += stdout_str[:5000] + f"\n... (truncated, total {len(stdout_str)} characters)"
                else:
                    output += stdout_str
            
            error_msg = None
            if stderr_str:
                error_msg = f"Curl stderr: {stderr_str}"
            elif not success:
                error_msg = f"Curl exited with code {process.returncode}"
            
            return ToolResult(
                success=success,
                output=output,
                error=error_msg,
                metadata={
                    "tool": "curl",
                    "command": curl_cmd,
                    "exit_code": process.returncode,
                    "response_size": len(stdout_str)
                }
            )
        
        except FileNotFoundError:
            return ToolResult(
                success=False,
                output="",
                error="curl is not installed or not found in PATH",
                metadata={"tool": "curl"}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Error executing curl: {str(e)}",
                metadata={"tool": "curl", "command": curl_cmd}
            )

