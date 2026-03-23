"""Price watch model for tracking product prices."""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class PriceWatch(Base):
    """Track products for price drop alerts."""

    __tablename__ = "price_watches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Product information (snapshot at time of watch creation)
    product_id = Column(String, nullable=False)  # External product ID
    product_title = Column(String, nullable=False)
    product_url = Column(String, nullable=False)  # Affiliate link
    product_image_url = Column(String, nullable=True)
    merchant = Column(String, nullable=True)

    # Price tracking
    original_price = Column(Float, nullable=False)  # Price when user added watch
    target_price = Column(Float, nullable=True)  # User's target price (optional)
    current_price = Column(Float, nullable=True)  # Latest checked price
    lowest_price = Column(Float, nullable=True)  # Lowest price seen
    price_drop_percentage = Column(Float, nullable=True)  # Current discount %

    # Status
    is_active = Column(Boolean, default=True)  # User can pause/resume
    alert_sent = Column(Boolean, default=False)  # Track if we sent notification
    last_checked = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="price_watches")

    def has_price_dropped(self) -> bool:
        """Check if price has dropped below target or significantly from original."""
        if not self.current_price:
            return False

        # If user set a target, check against that
        if self.target_price and self.current_price <= self.target_price:
            return True

        # Otherwise, alert if dropped 10% or more from original
        if self.current_price < self.original_price * 0.9:
            return True

        return False

    def calculate_drop_percentage(self) -> float:
        """Calculate current price drop percentage from original."""
        if not self.current_price or not self.original_price:
            return 0.0
        if self.original_price <= 0:
            return 0.0

        drop = (self.original_price - self.current_price) / self.original_price * 100
        return max(0.0, drop)  # Don't show negative (price increases)
