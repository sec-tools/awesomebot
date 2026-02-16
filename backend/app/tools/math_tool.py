"""Math calculation tool"""
import re
from typing import Dict, Any, List
from app.tools.base import Tool, ToolResult
from app.services.code_executor import CodeExecutor


class MathTool(Tool):
    """Tool for mathematical calculations"""
    
    def __init__(self):
        super().__init__()
        self.code_executor = CodeExecutor()
    
    def _get_description(self) -> str:
        return "Performs mathematical calculations by generating and executing Python code"
    
    def _get_patterns(self) -> List[str]:
        return [
            r'\b\d+\s*[\+\-\*\/\^%]\s*\d+',  # Basic arithmetic
            r'\bcalculate\b',
            r'\bcompute\b',
            r'\bsolve\b',
            r'\bwhat is\s+\d+',
            r'\bsum of\b',
            r'\bproduct of\b',
            r'\bdifference\b',
            r'\baverage of\b',
            r'\bmean of\b',
            r'\bfactorial\b',
            r'\bsquare root\b',
            r'\bpower of\b',
            r'\b\d+\s*(squared|cubed)\b',
        ]
    
    def _generate_code(self, message: str) -> str:
        """Generate Python code for the math operation"""
        message_lower = message.lower()
        
        # Complex expression detection (with parentheses, multiple operations)
        # Match expressions like: (15 + 25) * 2 / 4, 15% of 200, etc.
        complex_expr_match = re.search(r'[\d\s\+\-\*\/\(\)%\.]+', message)
        if complex_expr_match:
            expr = complex_expr_match.group().strip()
            # Check if it's a complex expression (has parentheses or multiple operators)
            if '(' in expr or expr.count('+') + expr.count('-') + expr.count('*') + expr.count('/') > 1:
                # Handle percentage expressions
                if '%' in message_lower and 'of' in message_lower:
                    percent_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*of\s*(\d+(?:\.\d+)?)', message_lower)
                    if percent_match:
                        percent, number = percent_match.groups()
                        return f"""# Calculating {percent}% of {number}
result = ({percent} / 100) * {number}
print(result)"""
                
                # Clean the expression for safe evaluation
                expr_clean = expr.replace('%', '/100*')
                return f"""# Solving: {expr}
result = {expr_clean}
print(result)"""
        
        # Simple arithmetic detection (fallback for basic operations)
        arithmetic_match = re.search(r'(\d+)\s*([\+\-\*\/])\s*(\d+)', message)
        if arithmetic_match:
            num1, op, num2 = arithmetic_match.groups()
            return f"""# Solving: {num1} {op} {num2}
result = {num1} {op} {num2}
print(result)"""
        
        # Calculate/compute detection
        if 'calculate' in message_lower or 'compute' in message_lower:
            numbers = re.findall(r'\d+(?:\.\d+)?', message)
            if len(numbers) >= 2:
                if 'sum' in message_lower or '+' in message:
                    nums_str = ' + '.join(numbers)
                    return f"""# Calculating sum
numbers = [{', '.join(numbers)}]
result = sum(numbers)
print(result)"""
                elif 'product' in message_lower or '*' in message or 'multiply' in message_lower:
                    return f"""# Calculating product
numbers = [{', '.join(numbers)}]
result = 1
for n in numbers:
    result *= n
print(result)"""
                elif 'average' in message_lower or 'mean' in message_lower:
                    return f"""# Calculating average
numbers = [{', '.join(numbers)}]
result = sum(numbers) / len(numbers)
print(result)"""
        
        # Factorial
        if 'factorial' in message_lower:
            num_match = re.search(r'\d+', message)
            if num_match:
                num = num_match.group()
                return f"""# Calculating factorial of {num}
import math
result = math.factorial({num})
print(result)"""
        
        # Square root
        if 'square root' in message_lower or 'sqrt' in message_lower:
            num_match = re.search(r'\d+(?:\.\d+)?', message)
            if num_match:
                num = num_match.group()
                return f"""# Calculating square root of {num}
import math
result = math.sqrt({num})
print(result)"""
        
        # Power
        if 'power' in message_lower or '^' in message or '**' in message:
            numbers = re.findall(r'\d+(?:\.\d+)?', message)
            if len(numbers) >= 2:
                return f"""# Calculating {numbers[0]} to the power of {numbers[1]}
result = {numbers[0]} ** {numbers[1]}
print(result)"""
        
        return None
    
    async def execute(self, user_message: str, context: Dict[str, Any]) -> ToolResult:
        """Execute math calculation"""
        
        code = self._generate_code(user_message)
        
        if not code:
            return ToolResult(
                success=False,
                output="",
                error="Could not generate code for this math operation",
                generated_code=None
            )
        
        # Execute the code
        execution_result = await self.code_executor.execute_python(code)
        
        return ToolResult(
            success=execution_result.get("success", False),
            output=execution_result.get("output", ""),
            error=execution_result.get("error", ""),
            generated_code=code,
            metadata={"tool": "math", "operation_type": "calculation"}
        )

