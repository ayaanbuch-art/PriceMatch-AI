"""User interaction model for recommendations."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class UserInteraction(Base):
    """User interaction model for tracking behavior."""

    __tablename__ = "user_interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Product info
    product_id = Column(String, nullable=False)
    product_category = Column(String, nullable=True)
    product_price = Column(Numeric(10, 2), nullable=True)

    # Interaction type
    interaction_type = Column(String, nullable=False)  # 'view', 'click', 'favorite', 'search'

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationship
    user = relationship("User", backref="interactions")
