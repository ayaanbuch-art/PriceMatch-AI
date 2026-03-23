"""Search schemas."""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, List


class GeminiAnalysis(BaseModel):
    """Gemini AI analysis result with fashion-specific fields."""
    item_type: str
    brand: Optional[str] = None
    style: str
    detailed_description: str
    colors: List[str]
    material: Optional[str] = None
    fit_silhouette: Optional[str] = None  # Fashion-specific fit description
    key_features: List[str]
    estimated_brand_tier: str
    season_occasion: str
    search_terms: List[str]
    search_query: Optional[str] = None  # Refined search string for retail matching
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
    rating: Optional[float] = None  # Product rating (0-5 stars)
    reviews_count: Optional[int] = None  # Number of reviews


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
