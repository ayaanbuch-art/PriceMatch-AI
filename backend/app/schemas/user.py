"""User schemas for request/response validation."""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class AppleSignIn(BaseModel):
    """Schema for Apple Sign-In."""
    identity_token: str
    authorization_code: str
    user_id: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    full_name: Optional[str] = None
    profile_image_url: Optional[str] = None


class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    profile_image_url: Optional[str] = None
    auth_provider: str
    subscription_status: str
    subscription_tier: Optional[str] = "free"
    subscription_expires_at: Optional[datetime] = None
    is_premium: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    """Token data for JWT payload."""
    user_id: Optional[int] = None
