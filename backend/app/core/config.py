"""Configuration settings"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # App info
    APP_NAME: str = "AwesomeBot"
    VERSION: str = "2.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/awesomebot.db"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Ollama
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://ollama:11434")
    DEFAULT_MODEL: str = "qwen2:1.5b"
    
    # RAG
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # Performance optimizations
    MAX_WORKERS: int = 2  # Limit thread pool for memory efficiency
    CHUNK_SIZE: int = 512  # Smaller chunks for faster processing
    MAX_CONTEXT_MESSAGES: int = 10  # Limit conversation history
    STREAM_CHUNK_SIZE: int = 64  # Smaller streaming chunks for responsiveness
    
    # Code execution
    CODE_TIMEOUT: int = 10  # seconds
    MAX_OUTPUT_LENGTH: int = 10000  # characters
    
    # File upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "./data/uploads"
    
    # Memory optimization
    ENABLE_GARBAGE_COLLECTION: bool = True
    GC_THRESHOLD: int = 100  # Run GC every N requests
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env


settings = Settings()
