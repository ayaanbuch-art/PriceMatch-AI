"""Search history model."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base


class SearchHistory(Base):
    """Search history model for tracking user searches."""

    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Image and analysis
    image_url = Column(String, nullable=True)  # S3 URL (nullable for text searches)
    search_query = Column(Text, nullable=True)  # Generated search terms
    gemini_analysis = Column(JSONB, nullable=False)  # Full Gemini response

    # Results
    results_data = Column(JSONB, nullable=True)  # Product results

    # Metadata
    search_type = Column(String, nullable=True)  # 'clothing', 'shoes', 'accessories'

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationship
    user = relationship("User", backref="searches")
