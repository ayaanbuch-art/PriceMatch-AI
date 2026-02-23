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


@router.get("/style-insights")
async def get_style_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get personalized style insights for premium users.
    Analyzes search history to generate style profile, color palette, and tips.
    """
    from collections import Counter
    import re

    now = datetime.now(timezone.utc)

    # Get all user searches with Gemini analysis
    searches = db.query(SearchHistory).filter(
        SearchHistory.user_id == current_user.id
    ).order_by(SearchHistory.created_at.desc()).all()

    total_searches = len(searches)

    # Get favorites count
    total_favorites = db.query(Favorite).filter(
        Favorite.user_id == current_user.id
    ).count()

    # Extract data from Gemini analysis
    all_colors = []
    all_styles = []
    all_item_types = []
    all_brands = []
    recent_searches = []  # Last 30 days

    thirty_days_ago = now - timedelta(days=30)

    for search in searches:
        analysis = search.gemini_analysis or {}

        # Extract colors
        colors = analysis.get("colors", [])
        if isinstance(colors, list):
            all_colors.extend(colors)

        # Extract style
        style = analysis.get("style", "")
        if style:
            all_styles.append(style.lower())

        # Extract item type
        item_type = analysis.get("item_type", "")
        if item_type:
            all_item_types.append(item_type.lower())

        # Extract brand tier
        brand_tier = analysis.get("estimated_brand_tier", "")
        if brand_tier:
            all_brands.append(brand_tier.lower())

        # Track recent searches
        if search.created_at and search.created_at >= thirty_days_ago:
            recent_searches.append(search)

    # Calculate style profile percentages
    style_keywords = {
        "casual": ["casual", "relaxed", "everyday", "comfortable", "laid-back"],
        "streetwear": ["streetwear", "urban", "street", "hip-hop", "skater"],
        "minimalist": ["minimalist", "minimal", "simple", "clean", "basic"],
        "classic": ["classic", "timeless", "traditional", "vintage", "retro"],
        "athletic": ["athletic", "sport", "active", "performance", "workout"],
        "bohemian": ["bohemian", "boho", "hippie", "free-spirited", "eclectic"],
        "elegant": ["elegant", "formal", "sophisticated", "luxury", "premium"],
        "trendy": ["trendy", "fashion-forward", "modern", "contemporary", "current"]
    }

    style_counts = {style: 0 for style in style_keywords}
    total_style_matches = 0

    for style_text in all_styles:
        for style_name, keywords in style_keywords.items():
            if any(keyword in style_text for keyword in keywords):
                style_counts[style_name] += 1
                total_style_matches += 1

    # Also check item types for style hints
    for item_type in all_item_types:
        for style_name, keywords in style_keywords.items():
            if any(keyword in item_type for keyword in keywords):
                style_counts[style_name] += 1
                total_style_matches += 1

    # Calculate percentages (with minimum if user has searches)
    style_profile = []
    if total_style_matches > 0:
        for style_name, count in sorted(style_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = round((count / total_style_matches) * 100) if total_style_matches > 0 else 0
            if percentage > 0 or (total_searches > 0 and len(style_profile) < 4):
                style_profile.append({
                    "name": style_name.title(),
                    "percentage": max(percentage, 5) if total_searches > 0 else percentage
                })
    else:
        # Default profile for new users
        style_profile = [
            {"name": "Casual", "percentage": 25},
            {"name": "Streetwear", "percentage": 25},
            {"name": "Minimalist", "percentage": 25},
            {"name": "Classic", "percentage": 25}
        ]

    # Take top 4 styles
    style_profile = style_profile[:4]

    # Extract and count colors for palette
    color_counter = Counter()
    for color in all_colors:
        # Clean up color names
        clean_color = color.strip().lower()
        # Remove pantone references for grouping
        clean_color = re.sub(r'\(pantone.*?\)', '', clean_color).strip()
        if clean_color and len(clean_color) > 2:
            color_counter[clean_color] += 1

    # Map colors to hex codes and names
    color_hex_map = {
        "black": ("#1A1A1A", "Black"),
        "white": ("#F5F5F5", "White"),
        "navy": ("#1A1A2E", "Navy"),
        "cream": ("#F5F5DC", "Cream"),
        "brown": ("#8B4513", "Brown"),
        "slate": ("#2F4F4F", "Slate"),
        "burgundy": ("#800020", "Burgundy"),
        "gray": ("#808080", "Gray"),
        "grey": ("#808080", "Grey"),
        "blue": ("#4169E1", "Blue"),
        "red": ("#DC143C", "Red"),
        "green": ("#228B22", "Green"),
        "olive": ("#808000", "Olive"),
        "beige": ("#F5F5DC", "Beige"),
        "tan": ("#D2B48C", "Tan"),
        "camel": ("#C19A6B", "Camel"),
        "pink": ("#FFC0CB", "Pink"),
        "purple": ("#800080", "Purple"),
        "orange": ("#FFA500", "Orange"),
        "yellow": ("#FFD700", "Yellow"),
        "gold": ("#FFD700", "Gold"),
        "silver": ("#C0C0C0", "Silver"),
        "charcoal": ("#36454F", "Charcoal"),
        "ivory": ("#FFFFF0", "Ivory"),
        "khaki": ("#C3B091", "Khaki"),
        "coral": ("#FF7F50", "Coral"),
        "teal": ("#008080", "Teal"),
        "maroon": ("#800000", "Maroon"),
        "off-white": ("#FAF9F6", "Off-White"),
    }

    # Get top colors with hex codes
    color_palette = []
    seen_colors = set()
    for color_name, count in color_counter.most_common(10):
        # Find matching color in map
        for key, (hex_code, display_name) in color_hex_map.items():
            if key in color_name and display_name not in seen_colors:
                color_palette.append({
                    "hex": hex_code,
                    "name": display_name
                })
                seen_colors.add(display_name)
                break

        if len(color_palette) >= 5:
            break

    # If not enough colors, add defaults
    default_colors = [
        {"hex": "#1A1A2E", "name": "Navy"},
        {"hex": "#F5F5DC", "name": "Cream"},
        {"hex": "#808080", "name": "Gray"},
        {"hex": "#228B22", "name": "Forest"},
        {"hex": "#800020", "name": "Burgundy"}
    ]
    while len(color_palette) < 5:
        for dc in default_colors:
            if dc["name"] not in seen_colors:
                color_palette.append(dc)
                seen_colors.add(dc["name"])
                if len(color_palette) >= 5:
                    break

    # Calculate style score (0-100)
    base_score = 50
    search_bonus = min(total_searches * 2, 20)  # Up to 20 points for searches
    favorites_bonus = min(total_favorites * 3, 15)  # Up to 15 points for favorites
    variety_bonus = min(len(set(all_item_types)) * 2, 10)  # Up to 10 points for variety
    recent_activity_bonus = min(len(recent_searches) * 2, 5)  # Up to 5 points for recent activity

    style_score = min(base_score + search_bonus + favorites_bonus + variety_bonus + recent_activity_bonus, 100)

    # Determine style level based on score
    if style_score >= 90:
        style_level = "Style Icon"
    elif style_score >= 80:
        style_level = "Trend Setter"
    elif style_score >= 70:
        style_level = "Fashion Forward"
    elif style_score >= 60:
        style_level = "Style Explorer"
    else:
        style_level = "Getting Started"

    # Get trending items from recent searches
    item_type_counter = Counter(all_item_types)
    trending_items = []
    trend_growth = ["+42%", "+38%", "+31%", "+27%", "+23%", "+19%"]

    for i, (item_type, count) in enumerate(item_type_counter.most_common(4)):
        trending_items.append({
            "name": item_type.title(),
            "growth": trend_growth[i] if i < len(trend_growth) else "+15%",
            "count": count
        })

    # If no trending items, use defaults
    if not trending_items:
        trending_items = [
            {"name": "Hoodies", "growth": "+42%", "count": 0},
            {"name": "Sneakers", "growth": "+38%", "count": 0},
            {"name": "T-Shirts", "growth": "+31%", "count": 0},
            {"name": "Jackets", "growth": "+27%", "count": 0}
        ]

    # Generate AI style tips based on user's actual data
    style_tips = []

    # Tip based on dominant style
    if style_profile and style_profile[0]["percentage"] > 30:
        dominant_style = style_profile[0]["name"]
        style_tips.append({
            "category": "Style Match",
            "tip": f"Your searches show a strong preference for {dominant_style} styles. Look for pieces that combine this with complementary aesthetics for a unique look."
        })

    # Tip based on colors
    if color_palette:
        top_colors = [c["name"] for c in color_palette[:3]]
        style_tips.append({
            "category": "Color Advice",
            "tip": f"Your favorite colors appear to be {', '.join(top_colors)}. These work well together - consider building a capsule wardrobe around them."
        })

    # Tip based on variety
    unique_types = len(set(all_item_types))
    if unique_types > 5:
        style_tips.append({
            "category": "Wardrobe Variety",
            "tip": f"Great variety! You've explored {unique_types} different item types. This versatility helps create more outfit combinations."
        })
    elif unique_types > 0:
        style_tips.append({
            "category": "Recommendations",
            "tip": "Try expanding your searches to include accessories and layering pieces to maximize outfit possibilities."
        })

    # Default tip if needed
    if len(style_tips) < 3:
        style_tips.append({
            "category": "Smart Shopping",
            "tip": "Investment pieces in classic styles offer better long-term value. Look for quality basics that mix with trendy items."
        })

    return {
        "style_score": style_score,
        "style_level": style_level,
        "stats": {
            "total_searches": total_searches,
            "total_favorites": total_favorites,
            "unique_styles": len(set(all_styles)) if all_styles else 0
        },
        "style_profile": style_profile,
        "color_palette": color_palette,
        "trending_items": trending_items,
        "style_tips": style_tips,
        "generated_at": now.isoformat()
    }
