"""Wardrobe models for storing user's clothing items and outfits."""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


# Association table for outfit items (many-to-many)
outfit_items = Table(
    'outfit_items',
    Base.metadata,
    Column('outfit_id', Integer, ForeignKey('outfits.id'), primary_key=True),
    Column('wardrobe_item_id', Integer, ForeignKey('wardrobe_items.id'), primary_key=True)
)


class WardrobeItem(Base):
    """User's wardrobe items."""

    __tablename__ = "wardrobe_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Item details (AI-analyzed)
    image_url = Column(String, nullable=False)  # Cloudinary URL
    item_type = Column(String, nullable=False)  # e.g., "top", "bottom", "dress", "shoes", "outerwear", "accessory"
    item_subtype = Column(String, nullable=True)  # e.g., "t-shirt", "jeans", "sneakers"
    brand = Column(String, nullable=True)
    color = Column(String, nullable=True)  # Primary color
    colors = Column(Text, nullable=True)  # JSON array of colors
    material = Column(String, nullable=True)
    pattern = Column(String, nullable=True)  # e.g., "solid", "striped", "floral"

    # Style metadata
    style_tags = Column(Text, nullable=True)  # JSON array: ["casual", "streetwear", "minimalist"]
    season = Column(String, nullable=True)  # "spring", "summer", "fall", "winter", "all"
    occasions = Column(Text, nullable=True)  # JSON array: ["casual", "work", "date", "gym"]
    formality = Column(String, nullable=True)  # "casual", "smart-casual", "formal"

    # User notes
    name = Column(String, nullable=True)  # User's custom name for the item
    notes = Column(Text, nullable=True)

    # Usage tracking
    times_worn = Column(Integer, default=0)
    last_worn = Column(DateTime(timezone=True), nullable=True)
    is_favorite = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="wardrobe_items")
    outfits = relationship("Outfit", secondary=outfit_items, back_populates="items")


class Outfit(Base):
    """Saved outfits combining multiple wardrobe items."""

    __tablename__ = "outfits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String, nullable=True)  # User's name for the outfit
    occasion = Column(String, nullable=True)  # What it's good for
    season = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # AI-generated or user-created
    is_ai_suggested = Column(Integer, default=0)
    ai_reasoning = Column(Text, nullable=True)  # Why AI suggested this combo

    # Usage
    times_worn = Column(Integer, default=0)
    last_worn = Column(DateTime(timezone=True), nullable=True)
    is_favorite = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="outfits")
    items = relationship("WardrobeItem", secondary=outfit_items, back_populates="outfits")
