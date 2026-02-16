"""MCP Server configuration model"""
from sqlalchemy import Column, String, Text, Boolean, DateTime
from datetime import datetime
import json
from app.core.database import Base


class MCPServer(Base):
    """Model Context Protocol server configuration"""
    __tablename__ = "mcp_servers"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    command = Column(String, nullable=False)  # Command to start the server
    args = Column(Text, nullable=True)  # JSON array of arguments
    env = Column(Text, nullable=True)  # JSON object of environment variables
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(String, nullable=False)  # Owner of the server config
    
    def get_args(self):
        """Get args as list"""
        if self.args:
            try:
                return json.loads(self.args)
            except:
                return []
        return []
    
    def get_env(self):
        """Get env as dict"""
        if self.env:
            try:
                return json.loads(self.env)
            except:
                return {}
        return {}

