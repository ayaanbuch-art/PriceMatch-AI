"""Analytics API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from typing import List

from ..database import get_db
from ..models import User, SearchHistory, UserInteraction, Favorite
from ..utils.auth import get_current_user
from ..services.recommendations import api_tracker

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/api-usage")
async def get_api_usage():
    """Get SerpAPI usage stats for monitoring (admin/dev endpoint)."""
    return {
        "serpapi_calls_today": api_tracker._calls_today,
        "serpapi_daily_limit": api_tracker.DAILY_LIMIT,
        "serpapi_remaining": api_tracker.get_remaining(),
        "last_reset_date": str(api_tracker._last_reset_date),
        "status": "ok" if api_tracker.can_make_call() else "limit_reached"
    }


@router.get("/stats")
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user analytics and stats."""

    # Use timezone-aware datetime for all comparisons
    now = datetime.now(timezone.utc)

    # Total searches
    total_searches = db.query(SearchHistory).filter(
        SearchHistory.user_id == current_user.id
    ).count()

    # Total favorites
    total_favorites = db.query(Favorite).filter(
        Favorite.user_id == current_user.id
    ).count()

    # Total product clicks (handle case where table might be empty or not exist)
    try:
        total_clicks = db.query(UserInteraction).filter(
            UserInteraction.user_id == current_user.id,
            UserInteraction.interaction_type == "click"
        ).count()
    except Exception:
        total_clicks = 0

    # Searches this week
    week_ago = now - timedelta(days=7)
    searches_this_week = db.query(SearchHistory).filter(
        SearchHistory.user_id == current_user.id,
        SearchHistory.created_at >= week_ago
    ).count()

    # Top categories from search history
    category_counts = db.query(
        SearchHistory.search_type,
        func.count(SearchHistory.id).label('count')
    ).filter(
        SearchHistory.user_id == current_user.id,
        SearchHistory.search_type.isnot(None)
    ).group_by(SearchHistory.search_type).order_by(
        func.count(SearchHistory.id).desc()
    ).limit(5).all()

    top_categories = [
        {"name": cat[0], "count": cat[1]}
        for cat in category_counts
    ]

    # Member since days - handle timezone-aware comparison
    if current_user.created_at:
        # Make sure we're comparing timezone-aware datetimes
        created_at = current_user.created_at
        if created_at.tzinfo is None:
            # If created_at is naive, assume UTC
            created_at = created_at.replace(tzinfo=timezone.utc)
        member_since_days = (now - created_at).days
    else:
        member_since_days = 0

    # Searches by day (last 7 days)
    searches_by_day = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        count = db.query(SearchHistory).filter(
            SearchHistory.user_id == current_user.id,
            SearchHistory.created_at >= day_start,
            SearchHistory.created_at < day_end
        ).count()

        searches_by_day.append({
            "day": day.strftime("%a"),
            "count": count
        })

    return {
        "total_searches": total_searches,
        "total_favorites": total_favorites,
        "total_clicks": total_clicks,
        "searches_this_week": searches_this_week,
        "top_categories": top_categories,
        "member_since_days": member_since_days,
        "searches_by_day": searches_by_day
    }
