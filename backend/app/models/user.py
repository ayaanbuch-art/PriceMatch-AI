"""User model."""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


# Subscription tier definitions
SUBSCRIPTION_TIERS = {
    "free": {
        "name": "Free",
        "monthly_scans": 20,
        "price": 0,
        "is_premium": False,
    },
    "basic": {
        "name": "Basic",
        "monthly_scans": 100,
        "price": 4.99,
        "is_premium": True,
    },
    "pro": {
        "name": "Pro",
        "monthly_scans": 500,
        "price": 9.99,
        "is_premium": True,
        "badge": "Best Value",
    },
    "unlimited": {
        "name": "Unlimited",
        "monthly_scans": -1,  # -1 means unlimited
        "price": 19.99,
        "is_premium": True,
        "badge": "Power Users & Resellers",
    },
}


class User(Base):
    """User model for authentication and profile."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)  # Nullable for OAuth users
    full_name = Column(String, nullable=True)
    profile_image_url = Column(String, nullable=True)

    # Authentication provider
    auth_provider = Column(String, default="email")  # 'email', 'apple', 'google'
    auth_provider_id = Column(String, nullable=True)  # ID from OAuth provider

    # Subscription
    subscription_status = Column(String, default="free")  # 'free', 'active', 'cancelled'
    subscription_tier = Column(String, default="free")  # 'free', 'basic', 'pro', 'unlimited'
    subscription_id = Column(String, nullable=True)  # Stripe subscription ID or Apple transaction ID
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    auto_renew_enabled = Column(Boolean, default=False)

    # Stripe customer ID
    stripe_customer_id = Column(String, nullable=True, unique=True)

    # Monthly usage tracking
    monthly_scans_used = Column(Integer, default=0)
    monthly_scans_reset_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Gamification relationships
    streak = relationship("UserStreak", back_populates="user", uselist=False)
    achievements = relationship("UserAchievement", back_populates="user")
    style_points = relationship("StylePoints", back_populates="user", uselist=False)

    @property
    def current_tier(self) -> str:
        """Get current subscription tier."""
        return self.subscription_tier or "free"

    def is_premium(self) -> bool:
        """Check if user has active premium subscription (any paid tier)."""
        from datetime import datetime, timezone
        if self.subscription_tier in ["basic", "pro", "unlimited"]:
            if self.subscription_status == "active" and self.subscription_expires_at:
                return self.subscription_expires_at > datetime.now(timezone.utc)
        return False

    def get_tier_info(self) -> dict:
        """Get current subscription tier information."""
        return SUBSCRIPTION_TIERS.get(self.subscription_tier, SUBSCRIPTION_TIERS["free"])

    def get_monthly_scan_limit(self) -> int:
        """Get monthly scan limit for current tier. Returns -1 for unlimited."""
        tier_info = self.get_tier_info()
        return tier_info.get("monthly_scans", 20)

    def get_remaining_scans(self) -> int:
        """Get remaining scans for this month. Returns -1 for unlimited."""
        limit = self.get_monthly_scan_limit()
        if limit == -1:
            return -1
        return max(0, limit - (self.monthly_scans_used or 0))

    def can_perform_scan(self) -> bool:
        """Check if user can perform a scan based on their tier and usage."""
        remaining = self.get_remaining_scans()
        return remaining == -1 or remaining > 0

    def increment_scan_count(self):
        """Increment the monthly scan counter."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        # Reset counter if it's a new month
        if self.monthly_scans_reset_at is None or self.monthly_scans_reset_at.month != now.month:
            self.monthly_scans_used = 0
            self.monthly_scans_reset_at = now

        self.monthly_scans_used = (self.monthly_scans_used or 0) + 1
