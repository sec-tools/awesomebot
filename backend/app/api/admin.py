"""Admin panel endpoints - with cache invalidation"""
import uuid
import subprocess
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.cache import settings_cache
from app.models.user import User, SystemSettings
from app.core.auth import get_admin_user

router = APIRouter()


class SystemPromptUpdate(BaseModel):
    """System prompt update"""
    system_prompt: str


class AISettingsUpdate(BaseModel):
    """AI settings update"""
    temperature: Optional[float] = 0.5
    max_tokens: Optional[int] = 1024
    enable_rag: Optional[bool] = True


class SettingResponse(BaseModel):
    """Setting response"""
    key: str
    value: str


@router.get("/settings/public")
async def get_public_settings(
    db: AsyncSession = Depends(get_db)
):
    """Get public system settings (available to all authenticated users)"""
    
    result = await db.execute(select(SystemSettings))
    settings = result.scalars().all()
    
    settings_dict = {s.key: s.value for s in settings}
    
    # Return only non-sensitive settings
    public_settings = {
        "temperature": settings_dict.get("temperature", "0.5"),
        "max_tokens": settings_dict.get("max_tokens", "1024"),
        "enable_rag": settings_dict.get("enable_rag", "true"),
        "awesome_gear_enabled": settings_dict.get("awesome_gear_enabled", "false")
    }
    
    return public_settings


@router.get("/settings")
async def get_settings(
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all system settings as a dictionary"""
    
    result = await db.execute(select(SystemSettings))
    settings = result.scalars().all()
    
    # Return as dictionary for easier frontend consumption
    settings_dict = {s.key: s.value for s in settings}
    
    # Add defaults for missing settings
    defaults = {
        "system_prompt": "You are a helpful AI assistant. Be concise and accurate.",
        "temperature": "0.5",
        "max_tokens": "1024",
        "enable_rag": "true"
    }
    
    for key, default_value in defaults.items():
        if key not in settings_dict:
            settings_dict[key] = default_value
    
    return settings_dict


@router.get("/settings/all")
async def get_all_settings_alias(
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all system settings (alias endpoint)"""
    
    result = await db.execute(select(SystemSettings))
    settings = result.scalars().all()
    
    # Return as dictionary
    settings_dict = {s.key: s.value for s in settings}
    
    # Add defaults for missing settings
    defaults = {
        "system_prompt": "You are a helpful AI assistant. Be concise and accurate.",
        "temperature": "0.5",
        "max_tokens": "1024",
        "enable_rag": "true"
    }
    
    for key, default_value in defaults.items():
        if key not in settings_dict:
            settings_dict[key] = default_value
    
    return settings_dict


@router.get("/settings/{key}")
async def get_setting(
    key: str,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific setting"""
    
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.key == key)
    )
    setting = result.scalar_one_or_none()
    
    if not setting:
        # Return default values
        defaults = {
            "system_prompt": "You are a helpful AI assistant. Be concise and accurate.",
            "temperature": "0.5",
            "max_tokens": "1024",
            "enable_rag": "true"
        }
        return {"key": key, "value": defaults.get(key, "")}
    
    return SettingResponse(key=setting.key, value=setting.value)


class SettingValueUpdate(BaseModel):
    """Setting value update"""
    value: str


@router.put("/settings/{key}")
async def update_setting(
    key: str,
    update: SettingValueUpdate,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a system setting"""
    
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.key == key)
    )
    setting = result.scalar_one_or_none()
    
    if setting:
        setting.value = update.value
    else:
        setting = SystemSettings(
            id=str(uuid.uuid4()),
            key=key,
            value=update.value
        )
        db.add(setting)
    
    await db.commit()
    
    # Invalidate cache for this setting
    await settings_cache.invalidate(key)
    
    return SettingResponse(key=setting.key, value=setting.value)


@router.post("/system-prompt")
async def update_system_prompt(
    request: SystemPromptUpdate,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update system prompt"""
    
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.key == "system_prompt")
    )
    setting = result.scalar_one_or_none()
    
    if setting:
        setting.value = request.system_prompt
    else:
        setting = SystemSettings(
            id=str(uuid.uuid4()),
            key="system_prompt",
            value=request.system_prompt
        )
        db.add(setting)
    
    await db.commit()
    
    # Invalidate cache for system prompt
    await settings_cache.invalidate("system_prompt")
    
    return {"status": "updated", "system_prompt": request.system_prompt}


@router.post("/settings")
async def update_settings_bulk(
    settings: dict,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update multiple settings at once"""
    
    for key, value in settings.items():
        result = await db.execute(
            select(SystemSettings).where(SystemSettings.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if setting:
            setting.value = str(value)
        else:
            setting = SystemSettings(
                id=str(uuid.uuid4()),
                key=key,
                value=str(value)
            )
            db.add(setting)
    
    await db.commit()
    
    # Invalidate all cached settings
    await settings_cache.invalidate()
    
    return {"status": "updated successfully", "settings": settings}


@router.post("/ai-settings")
async def update_ai_settings(
    request: AISettingsUpdate,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update AI settings"""
    
    settings_map = {
        "temperature": str(request.temperature),
        "max_tokens": str(request.max_tokens),
        "enable_rag": str(request.enable_rag).lower()
    }
    
    for key, value in settings_map.items():
        if value is not None:
            result = await db.execute(
                select(SystemSettings).where(SystemSettings.key == key)
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                setting.value = value
            else:
                setting = SystemSettings(
                    id=str(uuid.uuid4()),
                    key=key,
                    value=value
                )
                db.add(setting)
    
    await db.commit()
    
    # Invalidate all cached settings
    await settings_cache.invalidate()
    
    return {"status": "updated", "settings": settings_map}


async def restart_services_task():
    """Background task to restart services"""
    try:
        # Wait 2 seconds to allow response to be sent
        await asyncio.sleep(2)
        
        # Force restart by running the restart script
        # This script should be mounted in the container
        result = subprocess.run(
            ["/bin/sh", "/restart.sh"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print(f"Restart script completed: {result.returncode}")
        if result.stdout:
            print(f"STDOUT: {result.stdout}")
        if result.stderr:
            print(f"STDERR: {result.stderr}")
    except Exception as e:
        print(f"Error running restart script: {e}")
        # As fallback, just exit the process (Docker will restart if configured)
        import os
        import signal
        await asyncio.sleep(1)
        os.kill(os.getpid(), signal.SIGTERM)


@router.post("/restart")
async def restart_all_services(
    background_tasks: BackgroundTasks,
    admin_user: User = Depends(get_admin_user)
):
    """Restart all Docker services (admin only)"""
    
    # Schedule the restart in the background
    background_tasks.add_task(restart_services_task)
    
    return {
        "status": "restarting",
        "message": "Services are restarting. Please wait 15 seconds and the page will reload automatically."
    }


@router.get("/users", response_model=List[dict])
async def get_users(
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all users"""
    
    result = await db.execute(select(User))
    users = result.scalars().all()
    
    return [
        {
            "id": u.id,
            "username": u.username,
            "is_admin": u.is_admin,
            "created_at": u.created_at,
            "last_login": u.last_login
        }
        for u in users
    ]


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user (admin cannot delete themselves)"""
    
    # Prevent admin from deleting themselves
    if user_id == admin_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    # Get the user to delete
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete the user
    await db.delete(user)
    await db.commit()
    
    return {"success": True, "message": f"User {user.username} deleted successfully"}

