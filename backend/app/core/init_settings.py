"""Initialize system settings from configuration files"""
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import SystemSettings
import uuid


async def init_system_settings(db: AsyncSession) -> None:
    """Initialize system settings from SYSTEM_PROMPT.txt and defaults"""
    
    # Path to system prompt file (relative to project root)
    project_root = Path(__file__).parent.parent.parent.parent
    system_prompt_file = project_root / "SYSTEM_PROMPT.txt"
    
    # Load system prompt from file if it exists
    default_system_prompt = "You are a helpful AI assistant. Be concise and accurate."
    if system_prompt_file.exists():
        try:
            with open(system_prompt_file, 'r', encoding='utf-8') as f:
                default_system_prompt = f.read().strip()
            print(f"✅ Loaded system prompt from {system_prompt_file}")
        except Exception as e:
            print(f"⚠️  Failed to load system prompt from file: {e}")
    else:
        print(f"⚠️  System prompt file not found: {system_prompt_file}")
    
    # Define default settings
    default_settings = {
        "system_prompt": default_system_prompt,
        "temperature": "0.5",
        "max_tokens": "1024",
        "enable_rag": "true",
        "awesomegear_enabled": "true"
    }
    
    # Initialize each setting if it doesn't exist
    updated = False
    for key, default_value in default_settings.items():
        result = await db.execute(
            select(SystemSettings).where(SystemSettings.key == key)
        )
        existing = result.scalar_one_or_none()
        
        if not existing:
            # Setting doesn't exist, create it
            setting = SystemSettings(
                id=str(uuid.uuid4()),
                key=key,
                value=default_value
            )
            db.add(setting)
            await db.flush()  # Flush immediately to avoid UNIQUE constraint issues
            print(f"✅ Initialized setting: {key}")
            updated = True
        else:
            # Setting exists, optionally update system_prompt if file changed
            if key == "system_prompt" and system_prompt_file.exists():
                # Check if system prompt in DB is the default placeholder
                if existing.value == "You are a helpful AI assistant. Be concise and accurate.":
                    existing.value = default_value
                    print(f"✅ Updated system prompt from file")
                    updated = True
                else:
                    print(f"ℹ️  System prompt already customized, keeping existing value")
    
    if updated:
        await db.commit()
        print("✅ System settings initialized")
    else:
        print("ℹ️  All system settings already exist")
