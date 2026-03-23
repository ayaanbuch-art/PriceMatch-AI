"""Database models."""
from .user import User
from .search_history import SearchHistory
from .favorite import Favorite
from .user_interaction import UserInteraction
from .gamification import UserStreak, UserAchievement, StylePoints
from .feedback import SearchFeedback, PremiumPreviewUsage
from .price_watch import PriceWatch
from .community import DupeShare, DupeLike
from .wardrobe import WardrobeItem, Outfit

__all__ = [
    "User",
    "SearchHistory",
    "Favorite",
    "UserInteraction",
    "UserStreak",
    "UserAchievement",
    "StylePoints",
    "SearchFeedback",
    "PremiumPreviewUsage",
    "PriceWatch",
    "DupeShare",
    "DupeLike",
    "WardrobeItem",
    "Outfit"
]
