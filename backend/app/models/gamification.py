"""Gamification models for streaks, achievements, and rewards."""
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from ..database import Base


class UserStreak(Base):
    """Track user daily streaks."""
    __tablename__ = "user_streaks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_active_date = Column(DateTime, nullable=True)
    streak_freezes = Column(Integer, default=0)
    total_days_active = Column(Integer, default=0)
    weekly_activity = Column(JSON, default=list)  # Last 7 days
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="streak")

    def check_in(self) -> dict:
        """Process daily check-in and update streak."""
        today = datetime.utcnow().date()
        result = {
            "streak_continued": False,
            "streak_broken": False,
            "new_streak": False,
            "already_checked_in": False,
            "points_earned": 0
        }

        if self.last_active_date:
            last_date = self.last_active_date.date() if isinstance(self.last_active_date, datetime) else self.last_active_date
            days_diff = (today - last_date).days

            if days_diff == 0:
                result["already_checked_in"] = True
                return result
            elif days_diff == 1:
                # Continue streak
                self.current_streak += 1
                result["streak_continued"] = True
                result["points_earned"] = 10 + (self.current_streak * 2)  # Bonus for longer streaks
            elif days_diff == 2 and self.streak_freezes > 0:
                # Use streak freeze
                self.streak_freezes -= 1
                self.current_streak += 1
                result["streak_continued"] = True
                result["points_earned"] = 10
            else:
                # Streak broken
                self.current_streak = 1
                result["streak_broken"] = True
                result["points_earned"] = 10
        else:
            # First check-in
            self.current_streak = 1
            result["new_streak"] = True
            result["points_earned"] = 20  # Bonus for first check-in

        self.last_active_date = datetime.utcnow()
        self.total_days_active += 1

        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak

        # Update weekly activity
        self._update_weekly_activity()

        return result

    def _update_weekly_activity(self):
        """Update the last 7 days activity tracker."""
        if not self.weekly_activity:
            self.weekly_activity = [False] * 7

        # Shift and add today
        activity = list(self.weekly_activity)
        if len(activity) >= 7:
            activity = activity[1:] + [True]
        else:
            activity.append(True)
        self.weekly_activity = activity

    def to_dict(self) -> dict:
        return {
            "user_id": str(self.user_id),
            "current_streak": self.current_streak,
            "longest_streak": self.longest_streak,
            "last_active_date": self.last_active_date.isoformat() if self.last_active_date else None,
            "streak_freezes": self.streak_freezes,
            "total_days_active": self.total_days_active,
            "weekly_activity": self.weekly_activity or [False] * 7
        }


class UserAchievement(Base):
    """Track user achievement progress and unlocks."""
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(String, nullable=False)
    progress = Column(Integer, default=0)
    is_unlocked = Column(Boolean, default=False)
    unlocked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="achievements")


class StylePoints(Base):
    """Track user style points/XP."""
    __tablename__ = "style_points"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    total_points = Column(Integer, default=0)
    current_level = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="style_points")

    def add_points(self, points: int):
        """Add points and calculate level."""
        self.total_points += points
        self.current_level = self._calculate_level()

    def _calculate_level(self) -> int:
        """Calculate level based on total points."""
        # Level formula: sqrt(total_points / 100) + 1
        import math
        return max(1, int(math.sqrt(self.total_points / 100)) + 1)

    @property
    def points_to_next_level(self) -> int:
        """Calculate points needed for next level."""
        next_level_points = ((self.current_level) ** 2) * 100
        return max(0, next_level_points - self.total_points)

    @property
    def level_progress(self) -> float:
        """Calculate progress to next level (0-1)."""
        current_level_points = ((self.current_level - 1) ** 2) * 100
        next_level_points = (self.current_level ** 2) * 100
        level_range = next_level_points - current_level_points
        if level_range == 0:
            return 0
        progress_in_level = self.total_points - current_level_points
        return min(1.0, progress_in_level / level_range)

    def to_dict(self) -> dict:
        return {
            "total_points": self.total_points,
            "current_level": self.current_level,
            "points_to_next_level": self.points_to_next_level,
            "level_progress": self.level_progress
        }


# Achievement definitions
ACHIEVEMENTS = {
    # Search achievements
    "first_scan": {
        "title": "First Scan",
        "description": "Complete your first style scan",
        "icon": "camera.fill",
        "category": "search",
        "requirement": 1,
        "reward_points": 10,
        "tier": "bronze"
    },
    "scan_10": {
        "title": "Getting Started",
        "description": "Complete 10 style scans",
        "icon": "camera.fill",
        "category": "search",
        "requirement": 10,
        "reward_points": 50,
        "tier": "bronze"
    },
    "scan_50": {
        "title": "Style Seeker",
        "description": "Complete 50 style scans",
        "icon": "magnifyingglass",
        "category": "search",
        "requirement": 50,
        "reward_points": 100,
        "tier": "silver"
    },
    "scan_100": {
        "title": "Trend Hunter",
        "description": "Complete 100 style scans",
        "icon": "binoculars.fill",
        "category": "search",
        "requirement": 100,
        "reward_points": 250,
        "tier": "gold"
    },
    "scan_500": {
        "title": "Fashion Detective",
        "description": "Complete 500 style scans",
        "icon": "star.fill",
        "category": "search",
        "requirement": 500,
        "reward_points": 500,
        "tier": "platinum"
    },

    # Streak achievements
    "streak_3": {
        "title": "On Fire",
        "description": "Maintain a 3-day streak",
        "icon": "flame.fill",
        "category": "streak",
        "requirement": 3,
        "reward_points": 30,
        "tier": "bronze"
    },
    "streak_7": {
        "title": "Week Warrior",
        "description": "Maintain a 7-day streak",
        "icon": "flame.fill",
        "category": "streak",
        "requirement": 7,
        "reward_points": 100,
        "tier": "silver"
    },
    "streak_30": {
        "title": "Monthly Master",
        "description": "Maintain a 30-day streak",
        "icon": "flame.fill",
        "category": "streak",
        "requirement": 30,
        "reward_points": 500,
        "tier": "gold"
    },
    "streak_100": {
        "title": "Century Club",
        "description": "Maintain a 100-day streak",
        "icon": "trophy.fill",
        "category": "streak",
        "requirement": 100,
        "reward_points": 1000,
        "tier": "diamond"
    },

    # Collection achievements
    "fav_1": {
        "title": "First Love",
        "description": "Save your first favorite",
        "icon": "heart.fill",
        "category": "collection",
        "requirement": 1,
        "reward_points": 10,
        "tier": "bronze"
    },
    "fav_25": {
        "title": "Wishlist Builder",
        "description": "Save 25 favorites",
        "icon": "heart.fill",
        "category": "collection",
        "requirement": 25,
        "reward_points": 75,
        "tier": "silver"
    },
    "fav_100": {
        "title": "Collector",
        "description": "Save 100 favorites",
        "icon": "heart.fill",
        "category": "collection",
        "requirement": 100,
        "reward_points": 200,
        "tier": "gold"
    },

    # Premium achievements
    "premium_member": {
        "title": "VIP Status",
        "description": "Become a premium member",
        "icon": "crown.fill",
        "category": "premium",
        "requirement": 1,
        "reward_points": 100,
        "tier": "gold"
    }
}


def get_tier_streak_multiplier(tier: str) -> float:
    """Get streak point multiplier based on subscription tier."""
    multipliers = {
        "unlimited": 2.0,
        "pro": 1.5,
        "basic": 1.25,
        "free": 1.0
    }
    return multipliers.get(tier, 1.0)


def get_tier_max_freezes(tier: str) -> int:
    """Get max streak freezes based on subscription tier."""
    freezes = {
        "unlimited": 5,
        "pro": 3,
        "basic": 1,
        "free": 0
    }
    return freezes.get(tier, 0)
