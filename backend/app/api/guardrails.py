"""Guard Rails API endpoints - with cache invalidation"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.cache import settings_cache, CACHE_KEY_ENABLED_GUARDRAILS
from app.models.user import User
from app.models.guardrails import GuardRail
from app.core.auth import get_admin_user
from app.services.guardrails_service import GuardRailsService

router = APIRouter()


class GuardRailUpdate(BaseModel):
    """Guard rail enable/disable"""
    enabled: bool


@router.get("/")
async def list_guardrails(
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """List all guard rails with their status"""
    
    # Get all guard rails from DB
    result = await db.execute(select(GuardRail))
    db_rails = {rail.id: rail for rail in result.scalars().all()}
    
    # Get available guard rails from service
    available_rails = GuardRailsService.get_all_guardrails()
    
    # Combine info
    rails_list = []
    for rail_id, info in available_rails.items():
        db_rail = db_rails.get(rail_id)
        rails_list.append({
            "id": rail_id,
            "name": info["name"],
            "description": info["description"],
            "enabled": db_rail.enabled if db_rail else False
        })
    
    return {"guardrails": rails_list}


@router.put("/{rail_id}")
async def update_guardrail(
    rail_id: str,
    update: GuardRailUpdate,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Enable or disable a guard rail"""
    
    # Check if valid rail
    available_rails = GuardRailsService.get_all_guardrails()
    if rail_id not in available_rails:
        raise HTTPException(status_code=404, detail="Guard rail not found")
    
    # Get or create guard rail in DB
    result = await db.execute(
        select(GuardRail).where(GuardRail.id == rail_id)
    )
    guard_rail = result.scalar_one_or_none()
    
    if guard_rail:
        guard_rail.enabled = update.enabled
    else:
        guard_rail = GuardRail(
            id=rail_id,
            name=available_rails[rail_id]["name"],
            description=available_rails[rail_id]["description"],
            enabled=update.enabled
        )
        db.add(guard_rail)
    
    await db.commit()
    
    # Invalidate guardrails cache
    await settings_cache.invalidate(CACHE_KEY_ENABLED_GUARDRAILS)
    
    return {
        "id": rail_id,
        "name": available_rails[rail_id]["name"],
        "enabled": update.enabled
    }


@router.get("/enabled")
async def get_enabled_guardrails(
    db: AsyncSession = Depends(get_db)
):
    """Get list of enabled guard rail IDs (used by chat system)"""
    
    result = await db.execute(
        select(GuardRail).where(GuardRail.enabled == True)
    )
    enabled_rails = result.scalars().all()
    
    return {
        "enabled": [rail.id for rail in enabled_rails]
    }

