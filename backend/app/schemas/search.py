"""Search schemas."""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, List


class GeminiAnalysis(BaseModel):
    """Gemini AI analysis result."""
    item_type: str
    brand: Optional[str] = None
    style: str
    detailed_description: str
    colors: List[str]
    material: Optional[str] = None
    key_features: List[str]
    estimated_brand_tier: str
    season_occasion: str
    search_terms: List[str]
    price_estimate: str


class Product(BaseModel):
    """Product information."""
    id: str
    title: str
    description: str
    price: float
    original_price: Optional[float] = None
    currency: str = "USD"
    image_url: str
    merchant: str
    affiliate_link: str
    similarity_percentage: int  # 0-100
    brand: Optional[str] = None
    category: Optional[str] = None


class SearchResult(BaseModel):
    """Complete search result."""
    id: int
    image_url: Optional[str] = None  # Optional for text-based searches
    analysis: GeminiAnalysis
    products: List[Product]
    created_at: datetime

    class Config:
        from_attributes = True


class SearchHistoryResponse(BaseModel):
    """Search history list response."""
    searches: List[SearchResult]
    total: int
