"""Products model for AwesomeGear"""
from sqlalchemy import Column, String, Float, Integer, Text
from app.core.database import Base


class Product(Base):
    """AwesomeGear product"""
    __tablename__ = "products"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=100)


