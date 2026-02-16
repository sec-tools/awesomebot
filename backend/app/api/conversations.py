"""Conversation management API"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.models import Conversation, Message
from app.models.user import User
from app.core.auth import get_current_user

router = APIRouter()


class ConversationResponse(BaseModel):
    """Conversation response model"""
    id: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Message response model"""
    id: str
    role: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[ConversationResponse])
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all conversations for the current user"""
    
    # Filter conversations by current user's username
    result = await db.execute(
        select(Conversation)
        .where(Conversation.username == current_user.username)
        .order_by(desc(Conversation.updated_at))
    )
    conversations = result.scalars().all()
    
    response = []
    for conv in conversations:
        result = await db.execute(
            select(Message).where(Message.conversation_id == conv.id)
        )
        message_count = len(result.scalars().all())
        
        response.append(ConversationResponse(
            id=conv.id,
            title=conv.title,
            message_count=message_count,
            created_at=conv.created_at,
            updated_at=conv.updated_at
        ))
    
    return response


@router.get("/{conversation_id}", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get messages for a conversation (only if user owns it)"""
    
    # First check if the conversation belongs to the current user
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = conv_result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation.username != current_user.username:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    
    return [MessageResponse.model_validate(msg) for msg in messages]


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation (only if user owns it)"""
    
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Security: Only allow users to delete their own conversations
    if conversation.username != current_user.username:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await db.delete(conversation)
    await db.commit()
    
    return {"status": "deleted"}

