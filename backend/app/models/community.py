"""Community models for dupe sharing."""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class DupeShare(Base):
    """User-shared dupe finds for the community."""

    __tablename__ = "dupe_shares"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Original (expensive) product info
    original_title = Column(String, nullable=False)
    original_brand = Column(String, nullable=True)
    original_price = Column(Float, nullable=False)
    original_image_url = Column(String, nullable=True)
    original_url = Column(String, nullable=True)

    # Dupe (cheap) product info
    dupe_title = Column(String, nullable=False)
    dupe_brand = Column(String, nullable=True)
    dupe_price = Column(Float, nullable=False)
    dupe_image_url = Column(String, nullable=True)
    dupe_url = Column(String, nullable=False)  # Affiliate link to buy
    dupe_merchant = Column(String, nullable=True)

    # Metadata
    category = Column(String, nullable=True)  # e.g., "hoodie", "jeans", "sneakers"
    caption = Column(Text, nullable=True)  # User's description/review
    savings_percentage = Column(Float, nullable=False)  # Auto-calculated

    # Engagement
    likes_count = Column(Integer, default=0)
    views_count = Column(Integer, default=0)

    # Status
    is_approved = Column(Integer, default=1)  # 1=approved, 0=pending, -1=rejected
    is_featured = Column(Integer, default=0)  # Staff picks

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="dupe_shares")
    likes = relationship("DupeLike", back_populates="dupe_share", cascade="all, delete-orphan")

    def calculate_savings(self) -> float:
        """Calculate savings percentage."""
        if self.original_price <= 0:
            return 0.0
        return ((self.original_price - self.dupe_price) / self.original_price) * 100


class DupeLike(Base):
    """Likes on dupe shares."""

    __tablename__ = "dupe_likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    dupe_share_id = Column(Integer, ForeignKey("dupe_shares.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Ensure user can only like once
    __table_args__ = (
        UniqueConstraint('user_id', 'dupe_share_id', name='unique_user_like'),
    )

    # Relationships
    user = relationship("User", backref="dupe_likes")
    dupe_share = relationship("DupeShare", back_populates="likes")
