"""Code executor tool"""
import re
from typing import Dict, Any, List, Tuple, Optional
from app.tools.base import Tool, ToolResult
from app.services.code_executor import CodeExecutor


class CodeExecutorTool(Tool):
    """Tool for executing arbitrary Python code"""
    
    def __init__(self):
        super().__init__()
        self.code_executor = CodeExecutor()
    
    def _get_description(self) -> str:
        return "Executes Python code in a secure sandbox"
    
    def _get_patterns(self) -> List[str]:
        return [
            # More flexible patterns for natural language
            r'\bwrite\s+and\s+(run|execute)',  # "write and run"
            r'\b(run|execute)\s+code\s+(that|to)',  # "run code that/to"
            r'\bwrite.*run.*code',  # "write...run...code" (flexible)
            r'\brun.*code.*print',  # "run code...print" 
            # Original patterns
            r'\brun\s+code\s+that\s+(executes?|runs?)',  # "run code that executes/runs X"
            r'\bwrite\s+code\s+.*\s+(and\s+)?(run|execute)',  # "write code ... and run"
            r'\bwrite\s+.*code.*\s+and\s+run\s+it',  # "write ... code and run it"
            r'\brun\s+(this\s+)?code\b',
            r'\bexecute\s+(this\s+)?code\b',
            r'\brun\s+(the\s+)?python\s+code\b',
            r'\brun\s+it\b',  # "run it" (when code is implied)
            r'\bexecute\s+it\b',  # "execute it"
            r'\bexecute\s+the\s+\w+\s+(shell\s+)?command',  # "execute the X command"
            r'```python',  # Code block
        ]
    
    def _extract_or_generate_code(self, message: str) -> Tuple[Optional[str], bool]:
        """Extract or generate Python code from message.
        Returns: (code or None, is_generated)
        """
        
        # Look for code blocks
        code_block_match = re.search(r'```python\s*\n(.*?)```', message, re.DOTALL)
        if code_block_match:
            return (code_block_match.group(1).strip(), False)
        
        # Look for inline code
        inline_code_match = re.search(r'`([^`]+)`', message)
        if inline_code_match:
            return (inline_code_match.group(1).strip(), False)
        
        # Look for "run this code:" or "run this:" pattern
        run_code_match = re.search(r'run\s+(?:this\s+)?(?:code)?:\s*(.+)', message, re.IGNORECASE | re.DOTALL)
        if run_code_match:
            potential_code = run_code_match.group(1).strip()
            # Check if it looks like Python code (has print, function calls, assignments, etc.)
            if re.search(r'(?:print\(|import |def |class |for |while |if |=)', potential_code):
                return (potential_code, False)
        
        # If no code markers, try to find Python-like syntax
        # Look for lines that look like Python code
        lines = message.split('\n')
        code_lines = []
        for line in lines:
            stripped = line.strip()
            if (stripped and 
                (stripped.startswith(('import ', 'from ', 'def ', 'class ', 'for ', 'while ', 'if ')) or
                 '=' in stripped or
                 stripped.startswith('print('))):
                code_lines.append(line)
        
        if code_lines:
            return ('\n'.join(code_lines), False)
        
        # If message asks to execute a command, generate code for it
        # This will fail due to security restrictions, showing users the sandbox limits
        command_match = re.search(r'executes?\s+(?:the\s+)?(\w+)\s+(?:shell\s+)?command', message, re.IGNORECASE)
        if command_match:
            command = command_match.group(1)
            code = f"""# Attempting to execute '{command}' command
import subprocess
result = subprocess.run(['{command}'], capture_output=True, text=True)
print(result.stdout)"""
            return (code, True)
        
        # Check for "generate/create/write code and run" patterns
        generate_patterns = [
            r'(?:generate|create|write).*?(?:using\s+)?python.*?(?:and\s+)?(?:run|execute)',
            r'(?:generate|create|make).*?(?:and\s+)?(?:run|execute)\s+(?:it|that)',
        ]
        
        for pattern in generate_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                # Try to understand what they want to generate
                
                # Password generation
                if re.search(r'password|pass', message, re.IGNORECASE):
                    # Extract requirements
                    length_match = re.search(r'(\d+)\s*(?:character|char|digit)', message, re.IGNORECASE)
                    length = int(length_match.group(1)) if length_match else 12
                    
                    # Check for specific requirements
                    requirements = []
                    if 'days of the week' in message.lower() or 'day of week' in message.lower():
                        code = f"""import random
import string

# Password based on days of the week
days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
password_chars = []

# Take first letter of each day
for day in days:
    password_chars.append(day[0])

# Pick {length} random characters from day initials
password = ''.join(random.choice(password_chars) for _ in range({length}))
print(f"Generated password: {{password}}")"""
                        return (code, True)
                    else:
                        code = f"""import random
import string

# Generate secure password
chars = string.ascii_letters + string.digits + string.punctuation
password = ''.join(random.choice(chars) for _ in range({length}))
print(f"Generated password: {{password}}")"""
                        return (code, True)
                
                # Random number/data generation
                if re.search(r'random|generate.*(?:number|data)', message, re.IGNORECASE):
                    code = f"""import random

# Generate random data
result = random.randint(1, 100)
print(f"Generated: {{result}}")"""
                    return (code, True)
                
                # Calculate/compute something
                if re.search(r'calculate|compute|find', message, re.IGNORECASE):
                    code = f"""# Calculation requested
# Please provide more specific details for calculation
import math

result = "Please specify what to calculate"
print(result)"""
                    return (code, True)
        
        # If request is "write code to do X and run it", attempt it
        # For commands/subprocess, this will fail and show the security restriction
        if re.search(r'write\s+code.*(?:and\s+)?(?:run|execute)', message, re.IGNORECASE):
            # Extract what they want to execute
            if 'command' in message.lower():
                # Extract command name if mentioned
                cmd_match = re.search(r'\b(id|ls|pwd|whoami|echo|cat|grep)\b', message, re.IGNORECASE)
                if cmd_match:
                    cmd = cmd_match.group(1)
                    code = f"""import subprocess
result = subprocess.run(['{cmd}'], capture_output=True, text=True)
print(result.stdout)"""
                    return (code, True)
            
            # Fallback: try to extract any code intent
            code = f"""# Request: {message[:80]}
# Note: The sandbox restricts certain operations for security.
# Attempting to fulfill your request...
print("If you need to run system commands, use your terminal directly.")
print("Sandbox allows: math, json, statistics modules")"""
            return (code, True)
        
        return (None, False)
    
    async def execute(self, user_message: str, context: Dict[str, Any]) -> ToolResult:
        """Execute Python code"""
        
        code, is_generated = self._extract_or_generate_code(user_message)
        
        if not code:
            return ToolResult(
                success=False,
                output="",
                error="No Python code found in message. Please provide code in ```python code blocks or inline `code`.",
                generated_code=None,
                metadata={"tool": "code_executor"}
            )
        
        # Execute the code
        execution_result = await self.code_executor.execute_python(code)
        
        return ToolResult(
            success=execution_result.get("success", False),
            output=execution_result.get("output", ""),
            error=execution_result.get("error", ""),
            generated_code=code,
            metadata={
                "tool": "code_executor", 
                "user_provided": not is_generated,
                "auto_generated": is_generated
            }
        )

