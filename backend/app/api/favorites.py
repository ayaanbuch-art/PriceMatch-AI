"""Favorites API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import User, Favorite, UserInteraction
from ..schemas import FavoriteCreate, FavoriteResponse
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@router.post("", response_model=FavoriteResponse)
async def create_favorite(
    favorite_data: FavoriteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a product to favorites."""

    # Check if already favorited
    existing = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.product_id == favorite_data.product_id
    ).first()

    if existing:
        return FavoriteResponse(**existing.__dict__)

    # Create favorite
    favorite = Favorite(
        user_id=current_user.id,
        product_id=favorite_data.product_id,
        product_data=favorite_data.product_data
    )
    db.add(favorite)

    # Track interaction
    interaction = UserInteraction(
        user_id=current_user.id,
        product_id=favorite_data.product_id,
        product_category=favorite_data.product_data.get("category"),
        product_price=favorite_data.product_data.get("price"),
        interaction_type="favorite"
    )
    db.add(interaction)

    db.commit()
    db.refresh(favorite)

    return FavoriteResponse(**favorite.__dict__)


@router.delete("/{product_id}")
async def delete_favorite(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a product from favorites."""

    favorite = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.product_id == product_id
    ).first()

    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")

    db.delete(favorite)
    db.commit()

    return {"message": "Favorite removed"}


@router.get("", response_model=List[FavoriteResponse])
async def get_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all user's favorited products."""

    favorites = db.query(Favorite).filter(
        Favorite.user_id == current_user.id
    ).order_by(Favorite.created_at.desc()).all()

    return [FavoriteResponse(**f.__dict__) for f in favorites]
