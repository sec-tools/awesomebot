"""File analysis tool"""
import re
from typing import Dict, Any, List
from app.tools.base import Tool, ToolResult
from app.services.code_executor import CodeExecutor


class FileAnalysisTool(Tool):
    """Tool for analyzing data and generating visualizations"""
    
    def __init__(self):
        super().__init__()
        self.code_executor = CodeExecutor()
    
    def _get_description(self) -> str:
        return "Analyzes data, generates statistics, and creates visualizations"
    
    def _get_patterns(self) -> List[str]:
        return [
            r'\banalyze\s+(the\s+)?data\b',
            r'\bgenerate\s+(a\s+)?(chart|graph|plot)\b',
            r'\bvisualize\b',
            r'\bstatistics\b',
            r'\bcreate\s+(a\s+)?(chart|graph)\b',
            r'\bplot\b',
        ]
    
    def _generate_analysis_code(self, message: str) -> str:
        """Generate code for data analysis"""
        
        message_lower = message.lower()
        
        # Simple data analysis template
        if 'analyze' in message_lower or 'statistics' in message_lower:
            code = """# Data Analysis Example
# Note: This is a template. Provide actual data for real analysis.

import statistics

# Example data
data = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

# Calculate statistics
mean = statistics.mean(data)
median = statistics.median(data)
stdev = statistics.stdev(data) if len(data) > 1 else 0
min_val = min(data)
max_val = max(data)

print(f"Data Analysis Results:")
print(f"Count: {len(data)}")
print(f"Mean: {mean:.2f}")
print(f"Median: {median:.2f}")
print(f"Std Dev: {stdev:.2f}")
print(f"Min: {min_val}")
print(f"Max: {max_val}")
print(f"Range: {max_val - min_val}")
"""
            return code
        
        # Visualization template
        if any(word in message_lower for word in ['chart', 'graph', 'plot', 'visualize']):
            code = """# Data Visualization Example
# Note: In sandbox, actual plotting is limited. This shows the code structure.

# Example data
labels = ['A', 'B', 'C', 'D', 'E']
values = [23, 45, 56, 78, 32]

print("Visualization Data:")
for label, value in zip(labels, values):
    bar = '█' * (value // 5)
    print(f"{label}: {bar} ({value})")

print("\\nData Summary:")
print(f"Total: {sum(values)}")
print(f"Average: {sum(values)/len(values):.2f}")
print(f"Highest: {max(values)} ({labels[values.index(max(values))]})")
print(f"Lowest: {min(values)} ({labels[values.index(min(values))]})")
"""
            return code
        
        return None
    
    async def execute(self, user_message: str, context: Dict[str, Any]) -> ToolResult:
        """Execute file analysis"""
        
        code = self._generate_analysis_code(user_message)
        
        if not code:
            return ToolResult(
                success=False,
                output="",
                error="Could not generate analysis code. Try being more specific about what to analyze.",
                generated_code=None,
                metadata={"tool": "file_analysis"}
            )
        
        # Execute the analysis code
        execution_result = await self.code_executor.execute_python(code)
        
        return ToolResult(
            success=execution_result.get("success", False),
            output=execution_result.get("output", ""),
            error=execution_result.get("error", ""),
            generated_code=code,
            metadata={"tool": "file_analysis", "analysis_type": "statistics"}
        )


