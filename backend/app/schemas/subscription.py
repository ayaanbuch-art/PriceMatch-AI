"""Subscription schemas."""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class SubscriptionStatus(BaseModel):
    """Subscription status response."""
    is_premium: bool
    status: str  # 'free', 'active', 'cancelled'
    expires_at: Optional[datetime] = None
    auto_renew_enabled: bool
    subscription_id: Optional[str] = None


class UsageStatus(BaseModel):
    """Usage status for free tier."""
    searches_today: int
    searches_remaining: int
    limit: int
    is_premium: bool


class AppleWebhook(BaseModel):
    """Apple App Store webhook payload."""
    notification_type: str
    subtype: Optional[str] = None
    data: dict
