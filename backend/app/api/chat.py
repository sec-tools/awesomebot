"""Chat API endpoints - OPTIMIZED with singleton services and caching"""
import uuid
import json
from datetime import datetime
from typing import Optional
from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.cache import settings_cache, CACHE_KEY_SYSTEM_PROMPT, CACHE_KEY_ENABLED_GUARDRAILS, CACHE_KEY_AWESOMEGEAR_ENABLED
from app.models import Conversation, Message
from app.models.user import User, SystemSettings
from app.services import OllamaService, RAGService
from app.services.chat_service import ChatService
from app.services.guardrails_service import GuardRailsService
from app.services.awesomegear_service import AwesomeGearService
from app.core.auth import get_current_user
from app.models.guardrails import GuardRail

router = APIRouter()


# Lazy-loaded singleton services using lru_cache
@lru_cache(maxsize=1)
def get_ollama_service_instance():
    """Singleton OllamaService."""
    return OllamaService()

@lru_cache(maxsize=1)
def get_rag_service_instance():
    """Singleton RAGService."""
    return RAGService()

@lru_cache(maxsize=1)
def get_chat_service_instance():
    """Singleton ChatService."""
    return ChatService()

@lru_cache(maxsize=1)
def get_guardrails_service_instance():
    """Singleton GuardRailsService."""
    return GuardRailsService()

@lru_cache(maxsize=1)
def get_gear_service_instance():
    """Singleton AwesomeGearService."""
    return AwesomeGearService()


# For backwards compatibility, create module-level references
ollama_service = get_ollama_service_instance()
rag_service = get_rag_service_instance()
chat_service = get_chat_service_instance()
guardrails_service = get_guardrails_service_instance()
gear_service = get_gear_service_instance()


@router.get("/tools")
async def get_available_tools(current_user: User = Depends(get_current_user)):
    """Get list of available tools"""
    tools = chat_service.get_available_tools()
    return {"tools": tools}


async def get_system_setting(db: AsyncSession, key: str, default: str) -> str:
    """Get system setting from cache or database."""
    # For system_prompt, always get fresh data to ensure immediate updates
    if key == "system_prompt":
        result = await db.execute(
            select(SystemSettings).where(SystemSettings.key == key)
        )
        setting = result.scalar_one_or_none()
        return setting.value if setting else default
    
    # Check cache first for other settings
    cached = await settings_cache.get(key)
    if cached is not None:
        return cached
    
    # Query database
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.key == key)
    )
    setting = result.scalar_one_or_none()
    value = setting.value if setting else default
    
    # Cache for next time
    await settings_cache.set(key, value)
    return value


async def get_enabled_guardrails(db: AsyncSession) -> list:
    """Get enabled guard rails from cache or database."""
    # Check cache first
    cached = await settings_cache.get(CACHE_KEY_ENABLED_GUARDRAILS)
    if cached is not None:
        return cached
    
    # Query database
    result = await db.execute(
        select(GuardRail).where(GuardRail.enabled == True)
    )
    enabled_rails = [rail.id for rail in result.scalars().all()]
    
    # Cache for next time
    await settings_cache.set(CACHE_KEY_ENABLED_GUARDRAILS, enabled_rails)
    return enabled_rails


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    conversation_id: Optional[str] = None
    use_rag: bool = True
    stream: bool = True


class ChatResponse(BaseModel):
    """Chat response model"""
    conversation_id: str
    message_id: str
    response: str


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a chat message (non-streaming)"""
    
    # Get or create conversation
    conversation_id = request.conversation_id or str(uuid.uuid4())
    
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        conversation = Conversation(
            id=conversation_id,
            username=current_user.username,  # Store username for filtering
            title=request.message[:50] + "..." if len(request.message) > 50 else request.message
        )
        db.add(conversation)
        await db.commit()
    
    # Save user message
    user_message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="user",
        content=request.message
    )
    db.add(user_message)
    await db.commit()
    
    # Build context
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    
    # Format messages for AI
    ai_messages = []
    
    # Get system prompt from settings
    system_prompt = await get_system_setting(
        db, 
        "system_prompt", 
        "You are a helpful AI assistant. Be concise and accurate."
    )
    
    # Inject current user info into prompt for AI visibility
    system_prompt = system_prompt.replace("{USERNAME}", current_user.username)
    system_prompt = system_prompt.replace("{IS_ADMIN}", str(current_user.is_admin))
    
    # Check if AwesomeGear is enabled and query contains product-related keywords
    product_context_added = False
    awesomegear_enabled = await get_system_setting(db, "awesomegear_enabled", "false")
    if awesomegear_enabled == "true":
        product_keywords = ["product", "price", "buy", "shop", "gear", "shirt", "mug", "hat", "bottle", "sticker", "awesomegear", "awesome gear", "apparel", "drinkware", "tech", "office"]
        if any(keyword in request.message.lower() for keyword in product_keywords):
            try:
                products = await gear_service.query_products(db, request.message)
                if products:
                    product_context = gear_service.format_products_response(products, request.message)
                    system_prompt += f"\n\nAwesomeGear Catalog Results:\n{product_context}\n\nIMPORTANT: Display the above catalog results to the user. Simply present the data as shown."
                    product_context_added = True
            except Exception as e:
                print(f"AwesomeGear query error: {e}")
    
    # Add RAG context if enabled
    if request.use_rag:
        context = await rag_service.get_context(request.message)
        if context:
            # Combine system prompt with RAG context
            combined_prompt = f"{system_prompt}\n\nRelevant context from uploaded documents:\n{context}"
            ai_messages.append({
                "role": "system",
                "content": combined_prompt
            })
        else:
            # Use system prompt alone
            ai_messages.append({
                "role": "system",
                "content": system_prompt
            })
    else:
        # Use system prompt alone
        ai_messages.append({
            "role": "system",
            "content": system_prompt
        })
    
    # Add conversation history (last 3 messages to reduce context size)
    for msg in messages[-3:]:
        ai_messages.append({
            "role": msg.role,
            "content": msg.content
        })
    
    # Get AI response
    response_text = await ollama_service.chat(ai_messages)
    
    # Save AI response
    ai_message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="assistant",
        content=response_text
    )
    db.add(ai_message)
    
    # Update conversation timestamp
    conversation.updated_at = datetime.utcnow()
    await db.commit()
    
    return ChatResponse(
        conversation_id=conversation_id,
        message_id=ai_message.id,
        response=response_text
    )


@router.post("/stream")
async def stream_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a chat message with streaming response"""
    
    # Get or create conversation
    conversation_id = request.conversation_id or str(uuid.uuid4())
    
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        conversation = Conversation(
            id=conversation_id,
            username=current_user.username,  # Store username for filtering
            title=request.message[:50] + "..." if len(request.message) > 50 else request.message
        )
        db.add(conversation)
        await db.commit()
    
    # Save user message
    user_message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="user",
        content=request.message
    )
    db.add(user_message)
    await db.commit()
    
    # Build context
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    
    # Format messages for AI
    ai_messages = []
    
    # OPTIMIZATION: Use cached system prompt if available
    # This avoids rebuilding the prompt on every message in the conversation
    if conversation.cached_system_prompt:
        # Use cached prompt from first message (includes products, RAG context, etc.)
        system_prompt = conversation.cached_system_prompt
    else:
        # Build fresh system prompt for new conversation
        system_prompt = await get_system_setting(
            db, 
            "system_prompt", 
            "You are a helpful AI assistant. Be concise and accurate."
        )
        
        # Apply guard rails if enabled (using cached results)
        enabled_rails = await get_enabled_guardrails(db)
        if enabled_rails:
            system_prompt = guardrails_service.apply_guardrails(system_prompt, enabled_rails)
        
        # Inject current user info into prompt for AI visibility FIRST
        # This ensures base prompt has user context before adding dynamic content
        system_prompt = system_prompt.replace("{USERNAME}", current_user.username)
        system_prompt = system_prompt.replace("{IS_ADMIN}", str(current_user.is_admin))
        
        # Check if AwesomeGear is enabled and query contains product-related keywords
        # Product results added AFTER user context so they appear later in prompt
        awesomegear_enabled = await get_system_setting(db, "awesomegear_enabled", "false")
        product_context_added = False
        if awesomegear_enabled == "true":
            product_keywords = ["product", "price", "buy", "shop", "gear", "shirt", "mug", "hat", "bottle", "sticker", "awesomegear", "awesome gear", "apparel", "drinkware", "tech", "office"]
            if any(keyword in request.message.lower() for keyword in product_keywords):
                try:
                    # Query AwesomeGear products (uses raw user input - vulnerable to SQL injection)
                    products = await gear_service.query_products(db, request.message)
                    if products:
                        product_context = gear_service.format_products_response(products, request.message)
                        system_prompt += f"\n\nAwesomeGear Catalog Results:\n{product_context}\n\nIMPORTANT: Display the above catalog results to the user. Simply present the data as shown."
                        product_context_added = True
                except Exception as e:
                    # Log error but don't fail the request
                    print(f"AwesomeGear query error: {e}")
        
        # Cache the built prompt with this conversation for performance
        conversation.cached_system_prompt = system_prompt
        await db.commit()
    
    # Get temperature and max_tokens from settings
    temperature = float(await get_system_setting(db, "temperature", "0.5"))
    max_tokens = int(await get_system_setting(db, "max_tokens", "1024"))
    
    # Add RAG context if enabled
    if request.use_rag:
        context = await rag_service.get_context(request.message)
        if context:
            # Combine system prompt with RAG context
            combined_prompt = f"{system_prompt}\n\nRelevant context from uploaded documents:\n{context}"
            ai_messages.append({
                "role": "system",
                "content": combined_prompt
            })
        else:
            # Use system prompt alone
            ai_messages.append({
                "role": "system",
                "content": system_prompt
            })
    else:
        # Use system prompt alone
        ai_messages.append({
            "role": "system",
            "content": system_prompt
        })
    
    # Add conversation history (last 3 messages to reduce context size)
    for msg in messages[-3:]:
        ai_messages.append({
            "role": msg.role,
            "content": msg.content
        })
    
    # Stream response with automatic tool execution
    async def generate():
        # First, send the conversation_id to the frontend
        yield json.dumps({"type": "conversation_id", "conversation_id": conversation_id}) + "\n"
        
        full_response = ""
        tool_used = False
        tool_name = ""
        tool_code = ""
        tool_output = ""
        tool_error = ""
        tool_metadata = {}
        
        async for chunk in chat_service.stream_chat_with_tools(ai_messages, temperature, max_tokens, db, current_user.username, conversation_id, is_admin=current_user.is_admin):
            # Parse JSON chunks
            try:
                data = json.loads(chunk)
                chunk_type = data.get("type", "text")
                content = data.get("content", "")
                
                if chunk_type == "text":
                    full_response += content
                    yield chunk  # Send JSON chunk to frontend
                elif chunk_type == "search_results":
                    # Search results bypass AI - add to response
                    full_response += content
                    tool_used = True
                    tool_name = "conversation_memory"
                    tool_output = content
                    yield chunk
                elif chunk_type == "tool_code":
                    tool_used = True
                    tool_code = content
                    tool_name = data.get("tool", "unknown")
                    yield chunk
                elif chunk_type == "tool_result":
                    tool_output = data.get("output", "")
                    tool_error = data.get("error", "")
                    tool_metadata = data.get("metadata", {})
                    yield chunk
                else:
                    # tool_detection, tool_execution, text_start, done
                    yield chunk
            except:
                # Fallback for non-JSON chunks
                full_response += chunk
                yield chunk
        
        # Save AI response with tool metadata
        metadata = {}
        if tool_used:
            metadata = {
                "tool_used": True,
                "tool_name": tool_name,
                "tool_code": tool_code,
                "tool_output": tool_output,
                "tool_error": tool_error,
                "tool_metadata": tool_metadata
            }
        
        # Store metadata as JSON in content
        full_content = full_response
        if tool_used:
            full_content += f"\n\n<!-- TOOL_METADATA: {json.dumps(metadata)} -->"
        
        ai_message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="assistant",
            content=full_content
        )
        db.add(ai_message)
        
        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        await db.commit()
    
    return StreamingResponse(generate(), media_type="text/plain")

