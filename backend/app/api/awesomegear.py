"""AwesomeGear API endpoints"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User, SystemSettings
from app.core.auth import get_current_user, get_admin_user
from app.services.awesomegear_service import AwesomeGearService

router = APIRouter()
gear_service = AwesomeGearService()


class ProductQuery(BaseModel):
    """Product search query"""
    query: str


class FeatureToggle(BaseModel):
    """Feature enable/disable"""
    enabled: bool


@router.post("/query")
async def query_products(
    request: ProductQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Query products using natural language"""
    
    # Check if feature is enabled
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.key == "awesomegear_enabled")
    )
    setting = result.scalar_one_or_none()
    
    if not setting or setting.value != "true":
        raise HTTPException(status_code=403, detail="AwesomeGear feature is not enabled")
    
    # Query products
    products = await gear_service.query_products(db, request.query)
    
    # Format response
    formatted_response = gear_service.format_products_response(products, request.query)
    
    return {
        "query": request.query,
        "products": products,
        "formatted_response": formatted_response,
        "count": len(products)
    }


@router.get("/status")
async def get_awesomegear_status(
    db: AsyncSession = Depends(get_db)
):
    """Check if AwesomeGear feature is enabled"""
    
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.key == "awesomegear_enabled")
    )
    setting = result.scalar_one_or_none()
    
    return {
        "enabled": setting.value == "true" if setting else False
    }


@router.put("/toggle")
async def toggle_awesomegear(
    request: FeatureToggle,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Enable or disable AwesomeGear feature"""
    
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.key == "awesomegear_enabled")
    )
    setting = result.scalar_one_or_none()
    
    if setting:
        setting.value = "true" if request.enabled else "false"
    else:
        setting = SystemSettings(
            id="awesomegear_enabled",
            key="awesomegear_enabled",
            value="true" if request.enabled else "false"
        )
        db.add(setting)
    
    await db.commit()
    
    return {
        "enabled": request.enabled
    }


