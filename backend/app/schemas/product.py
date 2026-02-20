"""Product schemas."""
from pydantic import BaseModel
from datetime import datetime
from typing import List


class ProductClick(BaseModel):
    """Track product click."""
    product_id: str
    affiliate_link: str


class FavoriteCreate(BaseModel):
    """Create favorite."""
    product_id: str
    product_data: dict


class FavoriteResponse(BaseModel):
    """Favorite response."""
    id: int
    product_id: str
    product_data: dict
    created_at: datetime

    class Config:
        from_attributes = True


class InteractionCreate(BaseModel):
    """Create user interaction."""
    product_id: str
    interaction_type: str  # 'view', 'click', 'favorite', 'search'
    product_category: str | None = None
    product_price: float | None = None
