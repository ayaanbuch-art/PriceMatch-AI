"""Pydantic schemas."""
from .user import (
    UserCreate,
    UserLogin,
    AppleSignIn,
    UserUpdate,
    UserResponse,
    Token,
    TokenData
)
from .search import (
    GeminiAnalysis,
    Product,
    SearchResult,
    SearchHistoryResponse
)
from .product import (
    ProductClick,
    FavoriteCreate,
    FavoriteResponse,
    InteractionCreate
)
from .subscription import (
    SubscriptionStatus,
    UsageStatus,
    AppleWebhook
)

__all__ = [
    "UserCreate",
    "UserLogin",
    "AppleSignIn",
    "UserUpdate",
    "UserResponse",
    "Token",
    "TokenData",
    "GeminiAnalysis",
    "Product",
    "SearchResult",
    "SearchHistoryResponse",
    "ProductClick",
    "FavoriteCreate",
    "FavoriteResponse",
    "InteractionCreate",
    "SubscriptionStatus",
    "UsageStatus",
    "AppleWebhook",
]
