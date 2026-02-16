"""Simple agent service for autonomous task execution"""
from typing import List, Dict, AsyncGenerator
from app.services.ollama_service import OllamaService
from app.services.code_executor import CodeExecutor


class AgentService:
    """Simple agent that can plan and execute tasks"""
    
    def __init__(self):
        self.ollama = OllamaService()
        self.code_executor = CodeExecutor()
    
    async def execute_task(self, task: str) -> AsyncGenerator[Dict[str, any], None]:
        """Execute a task with planning and execution steps"""
        
        # Step 1: Plan the task
        yield {"type": "status", "message": "🤔 Planning task..."}
        
        plan_prompt = f"""Break down this task into 3-5 simple steps:
Task: {task}

Respond with a numbered list of steps, nothing else."""
        
        plan_messages = [
            {"role": "system", "content": "You are a task planner. Create simple, clear steps."},
            {"role": "user", "content": plan_prompt}
        ]
        
        plan = await self.ollama.chat(plan_messages)
        yield {"type": "plan", "content": plan}
        
        # Step 2: Execute each step
        steps = [line.strip() for line in plan.split('\n') if line.strip() and line.strip()[0].isdigit()]
        
        context = []
        for i, step in enumerate(steps, 1):
            yield {"type": "status", "message": f"⚡ Executing step {i}/{len(steps)}..."}
            
            # Execute step
            step_prompt = f"""Previous steps context:
{chr(10).join(context) if context else 'No previous context'}

Current step: {step}

Execute this step. If you need to write code, provide Python code in a code block.
Be concise and practical."""
            
            step_messages = [
                {"role": "system", "content": "You are a helpful AI assistant executing tasks step by step."},
                {"role": "user", "content": step_prompt}
            ]
            
            result = ""
            async for chunk in self.ollama.stream_chat(step_messages):
                result += chunk
                yield {"type": "step_chunk", "step": i, "chunk": chunk}
            
            # Check if there's code to execute
            if "```python" in result:
                code = self._extract_code(result)
                if code:
                    yield {"type": "status", "message": "💻 Executing code..."}
                    exec_result = await self.code_executor.execute_python(code)
                    
                    if exec_result["success"]:
                        yield {"type": "code_result", "output": exec_result["output"]}
                        context.append(f"Step {i}: {step}\nResult: {exec_result['output']}")
                    else:
                        yield {"type": "code_error", "error": exec_result["error"]}
                        context.append(f"Step {i}: {step}\nError: {exec_result['error']}")
            else:
                context.append(f"Step {i}: {step}\nResult: {result[:200]}")
            
            yield {"type": "step_complete", "step": i}
        
        # Step 3: Synthesize results
        yield {"type": "status", "message": "📊 Synthesizing results..."}
        
        synthesis_prompt = f"""Task: {task}

Steps executed:
{chr(10).join(context)}

Provide a brief summary of what was accomplished."""
        
        synthesis_messages = [
            {"role": "system", "content": "You are summarizing task execution results."},
            {"role": "user", "content": synthesis_prompt}
        ]
        
        summary = ""
        async for chunk in self.ollama.stream_chat(synthesis_messages):
            summary += chunk
            yield {"type": "summary_chunk", "chunk": chunk}
        
        yield {"type": "complete", "message": "✅ Task completed!"}
    
    def _extract_code(self, text: str) -> str:
        """Extract Python code from markdown code blocks"""
        import re
        pattern = r"```python\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        return matches[0] if matches else ""
    
    async def close(self):
        """Close services"""
        await self.ollama.close()


