"""Favorite model."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class Favorite(Base):
    """Favorite model for saved products."""

    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Product info
    product_id = Column(String, nullable=False)  # External product ID
    product_data = Column(JSONB, nullable=False)  # Full product details

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    user = relationship("User", backref="favorites")

    # Unique constraint: one user can only favorite a product once
    __table_args__ = (
        UniqueConstraint('user_id', 'product_id', name='unique_user_product'),
    )
