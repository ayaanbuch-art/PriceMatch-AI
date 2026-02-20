"""Gamification API endpoints for streaks, achievements, and rewards."""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from ..database import get_db
from ..models import User
from ..models.gamification import (
    UserStreak, UserAchievement, StylePoints,
    ACHIEVEMENTS, get_tier_streak_multiplier, get_tier_max_freezes
)
from ..utils.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gamification", tags=["gamification"])


# MARK: - Schemas

class StreakResponse(BaseModel):
    user_id: str
    current_streak: int
    longest_streak: int
    last_active_date: Optional[str]
    streak_freezes: int
    total_days_active: int
    weekly_activity: List[bool]


class AchievementResponse(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    category: str
    requirement: int
    progress: int
    is_unlocked: bool
    unlocked_at: Optional[str]
    reward_points: int
    tier: str


class StylePointsResponse(BaseModel):
    total_points: int
    current_level: int
    points_to_next_level: int
    level_progress: float


class DailyRewardResponse(BaseModel):
    id: str
    day: int
    reward: str
    bonus_scans: int
    is_claimed: bool
    is_today: bool


class GamificationDataResponse(BaseModel):
    streak: StreakResponse
    achievements: List[AchievementResponse]
    daily_rewards: List[DailyRewardResponse]
    style_points: StylePointsResponse
    unlocked_badges: int
    total_badges: int


class CheckInResponse(BaseModel):
    success: bool
    message: str
    streak: StreakResponse
    points_earned: int
    new_achievements: Optional[List[AchievementResponse]]
    daily_reward: Optional[DailyRewardResponse]


class TrackActionRequest(BaseModel):
    action: str


# MARK: - Endpoints

@router.post("/check-in", response_model=CheckInResponse)
async def check_in(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Daily check-in to maintain streak."""
    # Get or create streak
    streak = db.query(UserStreak).filter(UserStreak.user_id == current_user.id).first()
    if not streak:
        streak = UserStreak(user_id=current_user.id)
        db.add(streak)

    # Process check-in
    result = streak.check_in()

    if result["already_checked_in"]:
        db.commit()
        return CheckInResponse(
            success=True,
            message="Already checked in today! Come back tomorrow.",
            streak=StreakResponse(**streak.to_dict()),
            points_earned=0,
            new_achievements=None,
            daily_reward=None
        )

    # Apply tier multiplier to points
    tier = current_user.current_tier or "free"
    multiplier = get_tier_streak_multiplier(tier)
    points_earned = int(result["points_earned"] * multiplier)

    # Update style points
    style_points = db.query(StylePoints).filter(StylePoints.user_id == current_user.id).first()
    if not style_points:
        style_points = StylePoints(user_id=current_user.id)
        db.add(style_points)
    style_points.add_points(points_earned)

    # Check for streak achievements
    new_achievements = check_streak_achievements(current_user.id, streak.current_streak, db)

    # Generate message
    if result["streak_continued"]:
        message = f"🔥 {streak.current_streak} day streak! Keep it up!"
    elif result["new_streak"]:
        message = "Welcome! Your style journey begins! 🎉"
    else:
        message = "New streak started! You got this! 💪"

    # Generate daily reward (simplified)
    daily_reward = None
    if streak.current_streak % 7 == 0:  # Weekly bonus
        daily_reward = DailyRewardResponse(
            id=f"weekly_{streak.current_streak}",
            day=streak.current_streak,
            reward="bonus",
            bonus_scans=5,
            is_claimed=True,
            is_today=True
        )

    db.commit()

    logger.info(f"User {current_user.id} checked in. Streak: {streak.current_streak}")

    return CheckInResponse(
        success=True,
        message=message,
        streak=StreakResponse(**streak.to_dict()),
        points_earned=points_earned,
        new_achievements=new_achievements,
        daily_reward=daily_reward
    )


@router.get("/data", response_model=GamificationDataResponse)
async def get_gamification_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all gamification data for user."""
    # Get streak
    streak = db.query(UserStreak).filter(UserStreak.user_id == current_user.id).first()
    if not streak:
        streak = UserStreak(user_id=current_user.id)
        db.add(streak)
        db.commit()
        db.refresh(streak)

    # Get achievements
    user_achievements = db.query(UserAchievement).filter(
        UserAchievement.user_id == current_user.id
    ).all()

    achievements_dict = {ua.achievement_id: ua for ua in user_achievements}
    achievements = []
    unlocked_count = 0

    for ach_id, ach_data in ACHIEVEMENTS.items():
        user_ach = achievements_dict.get(ach_id)
        is_unlocked = user_ach.is_unlocked if user_ach else False
        progress = user_ach.progress if user_ach else 0

        if is_unlocked:
            unlocked_count += 1

        achievements.append(AchievementResponse(
            id=ach_id,
            title=ach_data["title"],
            description=ach_data["description"],
            icon=ach_data["icon"],
            category=ach_data["category"],
            requirement=ach_data["requirement"],
            progress=progress,
            is_unlocked=is_unlocked,
            unlocked_at=user_ach.unlocked_at.isoformat() if user_ach and user_ach.unlocked_at else None,
            reward_points=ach_data["reward_points"],
            tier=ach_data["tier"]
        ))

    # Get style points
    style_points = db.query(StylePoints).filter(StylePoints.user_id == current_user.id).first()
    if not style_points:
        style_points = StylePoints(user_id=current_user.id)
        db.add(style_points)
        db.commit()
        db.refresh(style_points)

    # Generate daily rewards (7-day cycle)
    daily_rewards = []
    today_day = (streak.total_days_active % 7) + 1
    for day in range(1, 8):
        reward_type = "scans" if day < 7 else "bonus"
        bonus = day * 2 if day < 7 else 10
        daily_rewards.append(DailyRewardResponse(
            id=f"day_{day}",
            day=day,
            reward=reward_type,
            bonus_scans=bonus,
            is_claimed=day < today_day,
            is_today=day == today_day
        ))

    return GamificationDataResponse(
        streak=StreakResponse(**streak.to_dict()),
        achievements=achievements,
        daily_rewards=daily_rewards,
        style_points=StylePointsResponse(**style_points.to_dict()),
        unlocked_badges=unlocked_count,
        total_badges=len(ACHIEVEMENTS)
    )


@router.post("/track")
async def track_action(
    request: TrackActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Track a gamification action (scan, favorite, etc.)."""
    action = request.action

    # Map action to achievement category
    action_map = {
        "scan": ["first_scan", "scan_10", "scan_50", "scan_100", "scan_500"],
        "favorite": ["fav_1", "fav_25", "fav_100"],
        "share": [],
        "category_search": []
    }

    achievement_ids = action_map.get(action, [])
    new_achievements = []

    for ach_id in achievement_ids:
        if ach_id not in ACHIEVEMENTS:
            continue

        # Get or create user achievement
        user_ach = db.query(UserAchievement).filter(
            UserAchievement.user_id == current_user.id,
            UserAchievement.achievement_id == ach_id
        ).first()

        if not user_ach:
            user_ach = UserAchievement(
                user_id=current_user.id,
                achievement_id=ach_id,
                progress=0
            )
            db.add(user_ach)

        # Increment progress
        user_ach.progress += 1

        # Check if unlocked
        requirement = ACHIEVEMENTS[ach_id]["requirement"]
        if not user_ach.is_unlocked and user_ach.progress >= requirement:
            user_ach.is_unlocked = True
            user_ach.unlocked_at = datetime.utcnow()

            # Award points
            style_points = db.query(StylePoints).filter(
                StylePoints.user_id == current_user.id
            ).first()
            if style_points:
                style_points.add_points(ACHIEVEMENTS[ach_id]["reward_points"])

            new_achievements.append(AchievementResponse(
                id=ach_id,
                title=ACHIEVEMENTS[ach_id]["title"],
                description=ACHIEVEMENTS[ach_id]["description"],
                icon=ACHIEVEMENTS[ach_id]["icon"],
                category=ACHIEVEMENTS[ach_id]["category"],
                requirement=requirement,
                progress=user_ach.progress,
                is_unlocked=True,
                unlocked_at=user_ach.unlocked_at.isoformat(),
                reward_points=ACHIEVEMENTS[ach_id]["reward_points"],
                tier=ACHIEVEMENTS[ach_id]["tier"]
            ))

            logger.info(f"User {current_user.id} unlocked achievement: {ach_id}")

    db.commit()

    return {
        "success": True,
        "action": action,
        "new_achievements": new_achievements if new_achievements else None
    }


@router.post("/use-freeze")
async def use_streak_freeze(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Use a streak freeze to protect streak."""
    tier = current_user.current_tier or "free"
    max_freezes = get_tier_max_freezes(tier)

    if max_freezes == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Streak freezes are a premium feature. Upgrade to unlock!"
        )

    streak = db.query(UserStreak).filter(UserStreak.user_id == current_user.id).first()
    if not streak:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No streak found"
        )

    if streak.streak_freezes >= max_freezes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You already have the maximum {max_freezes} streak freezes"
        )

    # Premium users get automatic freeze replenishment
    streak.streak_freezes = min(streak.streak_freezes + 1, max_freezes)
    db.commit()

    return {
        "success": True,
        "message": "Streak freeze added!",
        "freezes_remaining": streak.streak_freezes
    }


def check_streak_achievements(user_id: int, current_streak: int, db: Session) -> List[AchievementResponse]:
    """Check and unlock streak-based achievements."""
    streak_achievements = ["streak_3", "streak_7", "streak_30", "streak_100"]
    new_achievements = []

    for ach_id in streak_achievements:
        if ach_id not in ACHIEVEMENTS:
            continue

        requirement = ACHIEVEMENTS[ach_id]["requirement"]
        if current_streak < requirement:
            continue

        user_ach = db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == ach_id
        ).first()

        if user_ach and user_ach.is_unlocked:
            continue

        if not user_ach:
            user_ach = UserAchievement(
                user_id=user_id,
                achievement_id=ach_id,
                progress=current_streak
            )
            db.add(user_ach)

        user_ach.is_unlocked = True
        user_ach.unlocked_at = datetime.utcnow()
        user_ach.progress = current_streak

        new_achievements.append(AchievementResponse(
            id=ach_id,
            title=ACHIEVEMENTS[ach_id]["title"],
            description=ACHIEVEMENTS[ach_id]["description"],
            icon=ACHIEVEMENTS[ach_id]["icon"],
            category=ACHIEVEMENTS[ach_id]["category"],
            requirement=requirement,
            progress=current_streak,
            is_unlocked=True,
            unlocked_at=user_ach.unlocked_at.isoformat(),
            reward_points=ACHIEVEMENTS[ach_id]["reward_points"],
            tier=ACHIEVEMENTS[ach_id]["tier"]
        ))

    return new_achievements
