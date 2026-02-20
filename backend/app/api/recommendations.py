"""Recommendations API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import User, UserInteraction
from ..schemas import Product, InteractionCreate
from ..utils.auth import get_current_user
from ..services.recommendations import recommendation_service

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("", response_model=List[Product])
async def get_recommendations(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get personalized product recommendations."""

    recommendations = await recommendation_service.get_recommendations_for_user(
        user=current_user,
        db=db,
        limit=limit
    )

    return recommendations


@router.get("/sections")
async def get_recommendation_sections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get personalized recommendation sections for the For You page."""
    sections = await recommendation_service.get_recommendation_sections(
        user=current_user,
        db=db
    )
    return {"sections": sections}


@router.post("/track")
async def track_interaction(
    interaction: InteractionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Track a user interaction (view, click, etc.)."""

    user_interaction = UserInteraction(
        user_id=current_user.id,
        product_id=interaction.product_id,
        product_category=interaction.product_category,
        product_price=interaction.product_price,
        interaction_type=interaction.interaction_type
    )

    db.add(user_interaction)
    db.commit()

    return {"message": "Interaction tracked"}
