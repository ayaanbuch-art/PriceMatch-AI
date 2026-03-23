"""Price watch API endpoints."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from ..database import get_db
from ..models import User, PriceWatch
from ..utils.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/price-watch", tags=["price-watch"])


# Pydantic schemas
class WatchProductRequest(BaseModel):
    """Request to watch a product for price drops."""
    product_id: str
    product_title: str
    product_url: str
    product_image_url: Optional[str] = None
    merchant: Optional[str] = None
    current_price: float
    target_price: Optional[float] = None  # Optional target price to alert at


class PriceWatchResponse(BaseModel):
    """Price watch item response."""
    id: int
    product_id: str
    product_title: str
    product_url: str
    product_image_url: Optional[str]
    merchant: Optional[str]
    original_price: float
    target_price: Optional[float]
    current_price: Optional[float]
    lowest_price: Optional[float]
    price_drop_percentage: Optional[float]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PriceWatchListResponse(BaseModel):
    """List of watched items."""
    watches: List[PriceWatchResponse]
    total: int


@router.post("/watch", response_model=PriceWatchResponse)
async def watch_product(
    request: WatchProductRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a product to the user's price watch list.
    User will be notified when price drops below target or by 10%+.
    """
    # Check if user already watching this product
    existing = db.query(PriceWatch).filter(
        PriceWatch.user_id == current_user.id,
        PriceWatch.product_id == request.product_id,
        PriceWatch.is_active == True
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already watching this product"
        )

    # Limit watches for free users
    watch_count = db.query(PriceWatch).filter(
        PriceWatch.user_id == current_user.id,
        PriceWatch.is_active == True
    ).count()

    max_watches = 5 if current_user.subscription_tier == "free" else 50
    if watch_count >= max_watches:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum {max_watches} watched items allowed. Upgrade for more."
        )

    # Create watch
    watch = PriceWatch(
        user_id=current_user.id,
        product_id=request.product_id,
        product_title=request.product_title,
        product_url=request.product_url,
        product_image_url=request.product_image_url,
        merchant=request.merchant,
        original_price=request.current_price,
        current_price=request.current_price,
        lowest_price=request.current_price,
        target_price=request.target_price,
        price_drop_percentage=0.0
    )

    db.add(watch)
    db.commit()
    db.refresh(watch)

    logger.info(f"User {current_user.id} watching product {request.product_id}")

    return PriceWatchResponse(
        id=watch.id,
        product_id=watch.product_id,
        product_title=watch.product_title,
        product_url=watch.product_url,
        product_image_url=watch.product_image_url,
        merchant=watch.merchant,
        original_price=watch.original_price,
        target_price=watch.target_price,
        current_price=watch.current_price,
        lowest_price=watch.lowest_price,
        price_drop_percentage=watch.price_drop_percentage,
        is_active=watch.is_active,
        created_at=watch.created_at
    )


@router.get("/watching", response_model=PriceWatchListResponse)
async def get_watched_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all products user is watching for price drops."""
    watches = db.query(PriceWatch).filter(
        PriceWatch.user_id == current_user.id,
        PriceWatch.is_active == True
    ).order_by(PriceWatch.created_at.desc()).all()

    return PriceWatchListResponse(
        watches=[
            PriceWatchResponse(
                id=w.id,
                product_id=w.product_id,
                product_title=w.product_title,
                product_url=w.product_url,
                product_image_url=w.product_image_url,
                merchant=w.merchant,
                original_price=w.original_price,
                target_price=w.target_price,
                current_price=w.current_price,
                lowest_price=w.lowest_price,
                price_drop_percentage=w.price_drop_percentage,
                is_active=w.is_active,
                created_at=w.created_at
            )
            for w in watches
        ],
        total=len(watches)
    )


@router.delete("/watch/{watch_id}")
async def unwatch_product(
    watch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a product from price watch list."""
    watch = db.query(PriceWatch).filter(
        PriceWatch.id == watch_id,
        PriceWatch.user_id == current_user.id
    ).first()

    if not watch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watch not found"
        )

    # Soft delete - just mark inactive
    watch.is_active = False
    db.commit()

    logger.info(f"User {current_user.id} unwatched product {watch.product_id}")

    return {"message": "Product removed from watch list"}


@router.post("/watch/{watch_id}/update-target")
async def update_target_price(
    watch_id: int,
    target_price: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update target price for a watched product."""
    watch = db.query(PriceWatch).filter(
        PriceWatch.id == watch_id,
        PriceWatch.user_id == current_user.id,
        PriceWatch.is_active == True
    ).first()

    if not watch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watch not found"
        )

    if target_price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target price must be positive"
        )

    watch.target_price = target_price
    watch.alert_sent = False  # Reset alert flag if target changed
    db.commit()

    return {"message": "Target price updated", "target_price": target_price}


@router.get("/check/{product_id}")
async def check_if_watching(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user is already watching a specific product."""
    watch = db.query(PriceWatch).filter(
        PriceWatch.user_id == current_user.id,
        PriceWatch.product_id == product_id,
        PriceWatch.is_active == True
    ).first()

    return {
        "is_watching": watch is not None,
        "watch_id": watch.id if watch else None
    }
