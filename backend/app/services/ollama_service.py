"""Ollama service for AI model interactions - OPTIMIZED"""
import httpx
import json
from typing import AsyncGenerator, List, Dict, Optional
from app.core.config import settings


class OllamaService:
    """
    Singleton service for interacting with Ollama API.
    Uses native /api/chat endpoint for optimal performance.
    """
    
    _instance: Optional["OllamaService"] = None
    _initialized: bool = False
    
    def __new__(cls) -> "OllamaService":
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize HTTP client with connection pooling."""
        if self._initialized:
            return
            
        self.base_url = settings.OLLAMA_HOST
        self.default_model = settings.DEFAULT_MODEL
        
        # Persistent connection pool with optimized settings
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                timeout=600.0,      # Total timeout (10 minutes for large contexts)
                connect=10.0,       # Connection timeout
                read=600.0,         # Read timeout (for streaming)
                write=10.0          # Write timeout
            ),
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
                keepalive_expiry=30.0
            )
            # Note: http2=True requires 'h2' package, disabled for simplicity
        )
        
        self._initialized = True
    
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion using native /api/chat endpoint.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum number of tokens to generate (from admin panel)
            
        Yields:
            Response text chunks as they arrive
        """
        
        payload = {
            "model": self.default_model,
            "messages": messages,  # Pass directly - Ollama handles formatting!
            "stream": True,
            "options": {
                "temperature": temperature,  # Use parameter value from admin panel
                "num_predict": max_tokens,   # Use max_tokens from admin panel
                "num_ctx": 2048,           # Balanced context window
                "repeat_penalty": 1.1,     # Reduce repetition
                "num_thread": 8,           # Use more CPU threads
                "num_gpu": 99,             # Use all available GPU layers
                "f16_kv": True,            # Use FP16 for KV cache (faster)
            }
        }
        
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            # Native chat API returns message.content
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
                        except json.JSONDecodeError:
                            continue
        except httpx.TimeoutException:
            yield "Error: Request timed out. Please try again."
        except httpx.HTTPStatusError as e:
            yield f"Error: HTTP {e.response.status_code}"
        except Exception as e:
            yield f"Error: {str(e)}"
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """
        Non-streaming chat completion.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum number of tokens to generate (from admin panel)
            
        Returns:
            Complete response text
        """
        
        payload = {
            "model": self.default_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,  # Use parameter value from admin panel
                "num_predict": max_tokens,   # Use max_tokens from admin panel
                "num_ctx": 2048,           # Balanced context
                "num_thread": 8,           # More CPU threads
                "num_gpu": 99,             # Use all GPU layers
                "f16_kv": True,            # FP16 KV cache
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            # Native chat API returns message.content
            return data.get("message", {}).get("content", "")
        except httpx.TimeoutException:
            return "Error: Request timed out. Please try again."
        except httpx.HTTPStatusError as e:
            return f"Error: HTTP {e.response.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def check_health(self) -> bool:
        """Check if Ollama is running and responsive."""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/tags",
                timeout=5.0  # Quick timeout for health checks
            )
            return response.status_code == 200
        except Exception:
            return False
    
    async def close(self):
        """Close the HTTP client gracefully."""
        if self.client:
            await self.client.aclose()
            self._initialized = False
            OllamaService._instance = None


# Module-level singleton getter for convenience
_ollama_service: Optional[OllamaService] = None

def get_ollama_service() -> OllamaService:
    """Get or create the singleton OllamaService instance."""
    global _ollama_service
    if _ollama_service is None:
        _ollama_service = OllamaService()
    return _ollama_service
