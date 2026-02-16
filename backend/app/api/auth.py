"""Authentication endpoints"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)

router = APIRouter()


class SignupRequest(BaseModel):
    """Signup request"""
    username: str
    password: str


class LoginRequest(BaseModel):
    """Login request"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    token_type: str = "bearer"
    username: str
    is_admin: bool


class UserResponse(BaseModel):
    """User response"""
    id: str
    username: str
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.post("/signup", response_model=TokenResponse)
async def signup(request: SignupRequest, db: AsyncSession = Depends(get_db)):
    """Create a new user account"""
    
    # Validate username
    if len(request.username) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be at least 3 characters"
        )
    
    if len(request.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )
    
    # Check if username exists
    result = await db.execute(
        select(User).where(User.username == request.username)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create user
    user = User(
        id=str(uuid.uuid4()),
        username=request.username,
        password_hash=hash_password(request.password),
        is_admin=False
    )
    
    db.add(user)
    await db.commit()
    
    # Create token
    token = create_access_token(user.id, user.username, user.is_admin)
    
    return TokenResponse(
        access_token=token,
        username=user.username,
        is_admin=user.is_admin
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with username and password"""
    
    # Find user
    result = await db.execute(
        select(User).where(User.username == request.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # Create token
    token = create_access_token(user.id, user.username, user.is_admin)
    
    return TokenResponse(
        access_token=token,
        username=user.username,
        is_admin=user.is_admin
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return UserResponse.model_validate(current_user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Refresh access token - generates a new token for the current user"""
    # Create new token with extended expiration
    token = create_access_token(current_user.id, current_user.username, current_user.is_admin)
    
    return TokenResponse(
        access_token=token,
        username=current_user.username,
        is_admin=current_user.is_admin
    )

