"""Secure code execution service"""
import asyncio
import sys
from io import StringIO
from typing import Dict
from app.core.config import settings


class CodeExecutor:
    """Lightweight code execution sandbox"""
    
    def __init__(self):
        self.timeout = settings.CODE_TIMEOUT
    
    async def execute_python(self, code: str) -> Dict[str, any]:
        """Execute Python code in a safe environment"""
        
        # Create output capture
        output = StringIO()
        error_output = StringIO()
        
        # Prepare safe modules
        import math
        import json
        import statistics
        import random
        import string
        import subprocess
        import re
        import urllib
        import urllib.request
        import urllib.parse
        import urllib.error
        
        # Ensure urllib has its submodules properly attached
        urllib.request = urllib.request
        urllib.parse = urllib.parse
        urllib.error = urllib.error
        
        # Create safe import function that only allows specific modules
        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            allowed_modules = {
                'math': math,
                'json': json,
                'statistics': statistics,
                'random': random,
                'string': string,
                'subprocess': subprocess,
                're': re,
                'urllib': urllib,
                'urllib.request': urllib.request,
                'urllib.parse': urllib.parse,
                'urllib.error': urllib.error,
            }
            if name in allowed_modules:
                module = allowed_modules[name]
                # For dotted imports (e.g., 'urllib.parse'), return the top-level package
                # Python's import machinery will handle accessing submodules
                if '.' in name:
                    top_level = name.split('.')[0]
                    if top_level in allowed_modules:
                        return allowed_modules[top_level]
                return module
            raise ImportError(f"Module '{name}' is not allowed")
        
        # Create safe globals with limited builtins
        safe_globals = {
            '__builtins__': {
                'print': None,  # Will be replaced with custom print
                '__import__': safe_import,
                'True': True,
                'False': False,
                'None': None,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'dict': dict,
                'list': list,
                'tuple': tuple,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'isinstance': isinstance,
                'type': type,
                'abs': abs,
                'min': min,
                'max': max,
                'sum': sum,
                'round': round,
                'sorted': sorted,
                'reversed': reversed,
                'any': any,
                'all': all,
                'hasattr': hasattr,
                'getattr': getattr,
                'setattr': setattr,
                # Exception types for error handling
                'Exception': Exception,
                'ValueError': ValueError,
                'TypeError': TypeError,
                'KeyError': KeyError,
                'IndexError': IndexError,
                'AttributeError': AttributeError,
                'ImportError': ImportError,
                'RuntimeError': RuntimeError,
            },
            'math': math,
            'json': json,
            'statistics': statistics,
            'subprocess': subprocess,
            're': re,
            'urllib': urllib,
            'random': random,
            'string': string,
        }
        
        # Create custom print that writes to output
        def safe_print(*args, sep=' ', end='\n', **kwargs):
            message = sep.join(str(arg) for arg in args) + end
            output.write(message)
        
        # Add print to builtins
        safe_globals['__builtins__']['print'] = safe_print
        
        try:
            # Compile code
            compiled_code = compile(code, '<user_code>', 'exec')
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self._run_code(compiled_code, safe_globals, output, error_output),
                timeout=self.timeout
            )
            
            return result
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "output": output.getvalue(),
                "error": f"Execution timeout ({self.timeout}s)"
            }
        except SyntaxError as e:
            return {
                "success": False,
                "output": output.getvalue(),
                "error": f"Syntax error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "output": output.getvalue(),
                "error": f"Compilation error: {str(e)}"
            }
        finally:
            output.close()
            error_output.close()
    
    async def _run_code(self, compiled_code, safe_globals, output, error_output):
        """Run compiled code in executor"""
        
        def _execute():
            try:
                # Redirect stdout/stderr
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = output
                sys.stderr = error_output
                
                # Execute
                exec(compiled_code, safe_globals)
                
                # Restore stdout/stderr
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                
                output_text = output.getvalue()
                error_text = error_output.getvalue()
                
                return {
                    "success": not error_text,  # Success if no errors
                    "output": output_text,
                    "error": error_text if error_text else ""
                }
            except Exception as e:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                return {
                    "success": False,
                    "output": output.getvalue(),
                    "error": f"Execution error: {str(e)}"
                }
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _execute)
