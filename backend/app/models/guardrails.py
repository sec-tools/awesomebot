"""Guard Rails model for prompt security"""
from sqlalchemy import Column, String, Boolean, Text
from app.core.database import Base


class GuardRail(Base):
    """Guard rail configuration"""
    __tablename__ = "guardrails"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    enabled = Column(Boolean, default=False)
    config = Column(Text, nullable=True)  # JSON string for configuration


