"""Community API for dupe sharing."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from ..database import get_db
from ..models import User, DupeShare, DupeLike
from ..utils.auth import get_current_user
from ..services.gemini import gemini_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/community", tags=["community"])


# Pydantic schemas
class ShareDupeRequest(BaseModel):
    """Request to share a dupe find."""
    original_title: str
    original_brand: Optional[str] = None
    original_price: float
    original_image_url: Optional[str] = None
    original_url: Optional[str] = None

    dupe_title: str
    dupe_brand: Optional[str] = None
    dupe_price: float
    dupe_image_url: Optional[str] = None
    dupe_url: str
    dupe_merchant: Optional[str] = None

    category: Optional[str] = None
    caption: Optional[str] = None


class DupeShareResponse(BaseModel):
    """Dupe share response."""
    id: int
    userId: int
    userName: Optional[str]

    originalTitle: str
    originalBrand: Optional[str]
    originalPrice: float
    originalImageUrl: Optional[str]

    dupeTitle: str
    dupeBrand: Optional[str]
    dupePrice: float
    dupeImageUrl: Optional[str]
    dupeUrl: str
    dupeMerchant: Optional[str]

    category: Optional[str]
    caption: Optional[str]
    savingsPercentage: float

    likesCount: int
    viewsCount: int
    isLikedByMe: bool
    isFeatured: bool

    createdAt: datetime

    class Config:
        from_attributes = True


class CommunityFeedResponse(BaseModel):
    """Community feed response."""
    dupes: List[DupeShareResponse]
    total: int
    hasMore: bool


class VerifyDupeRequest(BaseModel):
    """Request to verify if two products are valid dupes."""
    original_image_url: str
    dupe_image_url: str


class VerifyDupeResponse(BaseModel):
    """Response from dupe verification."""
    similarity_score: int
    is_valid_dupe: bool
    product_category: Optional[str] = None
    design_match: Optional[str] = None
    color_match: Optional[str] = None
    key_similarities: List[str] = []
    key_differences: List[str] = []
    verdict: str


@router.post("/verify-dupe", response_model=VerifyDupeResponse)
async def verify_dupe(
    request: VerifyDupeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Verify if two product images are similar enough to be a valid dupe.
    Uses AI vision to compare the original and dupe images.

    Returns similarity score (0-100) and whether it's a valid dupe.
    """
    if not request.original_image_url or not request.dupe_image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both image URLs are required"
        )

    # Validate URLs look like valid image URLs
    valid_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
    original_lower = request.original_image_url.lower()
    dupe_lower = request.dupe_image_url.lower()

    # Check URL format (basic validation)
    if not (request.original_image_url.startswith('http://') or
            request.original_image_url.startswith('https://')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Original image URL must be a valid HTTP/HTTPS URL"
        )

    if not (request.dupe_image_url.startswith('http://') or
            request.dupe_image_url.startswith('https://')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dupe image URL must be a valid HTTP/HTTPS URL"
        )

    try:
        result = await gemini_service.verify_dupe_similarity(
            request.original_image_url,
            request.dupe_image_url
        )

        return VerifyDupeResponse(
            similarity_score=result.get("similarity_score", 0),
            is_valid_dupe=result.get("is_valid_dupe", False),
            product_category=result.get("product_category"),
            design_match=result.get("design_match"),
            color_match=result.get("color_match"),
            key_similarities=result.get("key_similarities", []),
            key_differences=result.get("key_differences", []),
            verdict=result.get("verdict", "Verification failed")
        )
    except Exception as e:
        logger.error(f"Error verifying dupe: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify dupe. Please try again."
        )


@router.post("/share", response_model=DupeShareResponse)
async def share_dupe(
    request: ShareDupeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Share a dupe find with the community.
    """
    # Validate prices
    if request.original_price <= 0 or request.dupe_price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prices must be positive"
        )

    if request.dupe_price >= request.original_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dupe price must be less than original price"
        )

    # Rate limit: max 5 shares per day for free users
    from datetime import timedelta
    from sqlalchemy import func as sql_func

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    shares_today = db.query(DupeShare).filter(
        DupeShare.user_id == current_user.id,
        DupeShare.created_at >= today_start
    ).count()

    max_daily = 5 if current_user.subscription_tier == "free" else 20
    if shares_today >= max_daily:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum {max_daily} shares per day"
        )

    # Calculate savings
    savings = ((request.original_price - request.dupe_price) / request.original_price) * 100

    # Create share
    share = DupeShare(
        user_id=current_user.id,
        original_title=request.original_title[:200],
        original_brand=request.original_brand[:100] if request.original_brand else None,
        original_price=request.original_price,
        original_image_url=request.original_image_url,
        original_url=request.original_url,
        dupe_title=request.dupe_title[:200],
        dupe_brand=request.dupe_brand[:100] if request.dupe_brand else None,
        dupe_price=request.dupe_price,
        dupe_image_url=request.dupe_image_url,
        dupe_url=request.dupe_url,
        dupe_merchant=request.dupe_merchant[:100] if request.dupe_merchant else None,
        category=request.category[:50] if request.category else None,
        caption=request.caption[:500] if request.caption else None,
        savings_percentage=savings
    )

    db.add(share)
    db.commit()
    db.refresh(share)

    logger.info(f"User {current_user.id} shared dupe: {share.id}")

    return DupeShareResponse(
        id=share.id,
        userId=share.user_id,
        userName=current_user.full_name,
        originalTitle=share.original_title,
        originalBrand=share.original_brand,
        originalPrice=share.original_price,
        originalImageUrl=share.original_image_url,
        dupeTitle=share.dupe_title,
        dupeBrand=share.dupe_brand,
        dupePrice=share.dupe_price,
        dupeImageUrl=share.dupe_image_url,
        dupeUrl=share.dupe_url,
        dupeMerchant=share.dupe_merchant,
        category=share.category,
        caption=share.caption,
        savingsPercentage=share.savings_percentage,
        likesCount=0,
        viewsCount=0,
        isLikedByMe=False,
        isFeatured=share.is_featured == 1,
        createdAt=share.created_at
    )


@router.get("/feed", response_model=CommunityFeedResponse)
async def get_community_feed(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    category: Optional[str] = None,
    sort: str = Query("recent", regex="^(recent|popular|savings)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the community dupe feed.

    Sort options:
    - recent: Most recent first
    - popular: Most liked first
    - savings: Highest savings percentage first
    """
    query = db.query(DupeShare).filter(DupeShare.is_approved == 1)

    # Filter by category if specified
    if category:
        query = query.filter(DupeShare.category == category)

    # Get total count before pagination
    total = query.count()

    # Apply sorting
    if sort == "popular":
        query = query.order_by(desc(DupeShare.likes_count), desc(DupeShare.created_at))
    elif sort == "savings":
        query = query.order_by(desc(DupeShare.savings_percentage), desc(DupeShare.created_at))
    else:  # recent
        query = query.order_by(desc(DupeShare.created_at))

    # Paginate
    shares = query.offset(skip).limit(limit).all()

    # Get user's likes
    user_likes = set()
    if current_user:
        liked = db.query(DupeLike.dupe_share_id).filter(
            DupeLike.user_id == current_user.id,
            DupeLike.dupe_share_id.in_([s.id for s in shares])
        ).all()
        user_likes = {l[0] for l in liked}

    # Build response
    dupes = []
    for share in shares:
        dupes.append(DupeShareResponse(
            id=share.id,
            userId=share.user_id,
            userName=share.user.full_name if share.user else None,
            originalTitle=share.original_title,
            originalBrand=share.original_brand,
            originalPrice=share.original_price,
            originalImageUrl=share.original_image_url,
            dupeTitle=share.dupe_title,
            dupeBrand=share.dupe_brand,
            dupePrice=share.dupe_price,
            dupeImageUrl=share.dupe_image_url,
            dupeUrl=share.dupe_url,
            dupeMerchant=share.dupe_merchant,
            category=share.category,
            caption=share.caption,
            savingsPercentage=share.savings_percentage,
            likesCount=share.likes_count,
            viewsCount=share.views_count,
            isLikedByMe=share.id in user_likes,
            isFeatured=share.is_featured == 1,
            createdAt=share.created_at
        ))

    return CommunityFeedResponse(
        dupes=dupes,
        total=total,
        hasMore=(skip + limit) < total
    )


@router.post("/{share_id}/like")
async def like_dupe(
    share_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Like a dupe share."""
    share = db.query(DupeShare).filter(DupeShare.id == share_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="Dupe not found")

    # Check if already liked
    existing = db.query(DupeLike).filter(
        DupeLike.user_id == current_user.id,
        DupeLike.dupe_share_id == share_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Already liked")

    # Create like
    like = DupeLike(user_id=current_user.id, dupe_share_id=share_id)
    db.add(like)

    # Increment counter
    share.likes_count = (share.likes_count or 0) + 1
    db.commit()

    return {"message": "Liked", "likesCount": share.likes_count}


@router.delete("/{share_id}/like")
async def unlike_dupe(
    share_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unlike a dupe share."""
    like = db.query(DupeLike).filter(
        DupeLike.user_id == current_user.id,
        DupeLike.dupe_share_id == share_id
    ).first()

    if not like:
        raise HTTPException(status_code=404, detail="Like not found")

    db.delete(like)

    # Decrement counter
    share = db.query(DupeShare).filter(DupeShare.id == share_id).first()
    if share:
        share.likes_count = max(0, (share.likes_count or 0) - 1)

    db.commit()

    return {"message": "Unliked", "likesCount": share.likes_count if share else 0}


@router.get("/my-shares", response_model=CommunityFeedResponse)
async def get_my_shares(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's shared dupes."""
    query = db.query(DupeShare).filter(DupeShare.user_id == current_user.id)
    total = query.count()

    shares = query.order_by(desc(DupeShare.created_at)).offset(skip).limit(limit).all()

    dupes = []
    for share in shares:
        dupes.append(DupeShareResponse(
            id=share.id,
            userId=share.user_id,
            userName=current_user.full_name,
            originalTitle=share.original_title,
            originalBrand=share.original_brand,
            originalPrice=share.original_price,
            originalImageUrl=share.original_image_url,
            dupeTitle=share.dupe_title,
            dupeBrand=share.dupe_brand,
            dupePrice=share.dupe_price,
            dupeImageUrl=share.dupe_image_url,
            dupeUrl=share.dupe_url,
            dupeMerchant=share.dupe_merchant,
            category=share.category,
            caption=share.caption,
            savingsPercentage=share.savings_percentage,
            likesCount=share.likes_count,
            viewsCount=share.views_count,
            isLikedByMe=True,  # User's own post
            isFeatured=share.is_featured == 1,
            createdAt=share.created_at
        ))

    return CommunityFeedResponse(
        dupes=dupes,
        total=total,
        hasMore=(skip + limit) < total
    )


@router.delete("/{share_id}")
async def delete_share(
    share_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a dupe share (only owner can delete)."""
    share = db.query(DupeShare).filter(
        DupeShare.id == share_id,
        DupeShare.user_id == current_user.id
    ).first()

    if not share:
        raise HTTPException(status_code=404, detail="Share not found or not authorized")

    db.delete(share)
    db.commit()

    return {"message": "Deleted"}
