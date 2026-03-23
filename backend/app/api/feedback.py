"""Feedback API endpoints for AI improvement."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from ..database import get_db
from ..models import User, SearchFeedback, PremiumPreviewUsage
from ..utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback", tags=["feedback"])


# ============ Schemas ============

class FeedbackRequest(BaseModel):
    """Request body for submitting search feedback."""
    search_id: Optional[int] = None
    is_accurate: bool
    feedback_type: Optional[str] = None  # 'wrong_item', 'wrong_color', 'wrong_fit', 'wrong_brand', 'other'
    feedback_text: Optional[str] = None
    ai_detected_item: Optional[str] = None
    correct_item: Optional[str] = None
    ai_detected_fit: Optional[str] = None
    correct_fit: Optional[str] = None
    ai_detected_brand: Optional[str] = None
    correct_brand: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""
    success: bool
    message: str
    feedback_id: int


class PremiumPreviewStatus(BaseModel):
    """Status of user's premium preview allowance."""
    remaining_previews: int
    max_weekly_previews: int
    total_used_lifetime: int
    can_use_preview: bool
    resets_in_days: int  # Days until weekly reset


class UsePreviewResponse(BaseModel):
    """Response after using a premium preview."""
    success: bool
    remaining_previews: int
    message: str


# ============ Feedback Endpoints ============

@router.post("/submit", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit feedback on search results.

    This helps us improve the AI by learning from user corrections.
    """
    try:
        feedback = SearchFeedback(
            user_id=current_user.id,
            search_id=request.search_id,
            is_accurate=request.is_accurate,
            feedback_type=request.feedback_type,
            feedback_text=request.feedback_text,
            ai_detected_item=request.ai_detected_item,
            correct_item=request.correct_item,
            ai_detected_fit=request.ai_detected_fit,
            correct_fit=request.correct_fit,
            ai_detected_brand=request.ai_detected_brand,
            correct_brand=request.correct_brand
        )

        db.add(feedback)
        db.commit()
        db.refresh(feedback)

        # Log for monitoring
        if request.is_accurate:
            logger.info(f"Positive feedback from user {current_user.id}")
        else:
            logger.info(f"Negative feedback from user {current_user.id}: {request.feedback_type} - {request.feedback_text}")

        return FeedbackResponse(
            success=True,
            message="Thank you for your feedback! This helps us improve.",
            feedback_id=feedback.id
        )

    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save feedback")


@router.get("/stats")
async def get_feedback_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get feedback statistics (admin/debugging)."""
    # Count user's feedback
    user_feedback_count = db.query(SearchFeedback).filter(
        SearchFeedback.user_id == current_user.id
    ).count()

    positive_count = db.query(SearchFeedback).filter(
        SearchFeedback.user_id == current_user.id,
        SearchFeedback.is_accurate == True
    ).count()

    return {
        "total_feedback_given": user_feedback_count,
        "positive_feedback": positive_count,
        "negative_feedback": user_feedback_count - positive_count
    }


# ============ Premium Preview Endpoints ============

@router.get("/premium-preview/status", response_model=PremiumPreviewStatus)
async def get_premium_preview_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the user's premium preview status.

    Free users get 3 premium searches per week to experience premium features.
    """
    # Premium users don't need previews
    if current_user.is_premium():
        return PremiumPreviewStatus(
            remaining_previews=999,  # Unlimited for premium
            max_weekly_previews=999,
            total_used_lifetime=0,
            can_use_preview=True,
            resets_in_days=0
        )

    # Get or create preview usage record
    preview_usage = db.query(PremiumPreviewUsage).filter(
        PremiumPreviewUsage.user_id == current_user.id
    ).first()

    if not preview_usage:
        preview_usage = PremiumPreviewUsage(user_id=current_user.id)
        db.add(preview_usage)
        db.commit()
        db.refresh(preview_usage)

    remaining = preview_usage.get_remaining_previews()
    db.commit()  # Save any reset that happened

    # Calculate days until reset (next Monday)
    now = datetime.now(timezone.utc)
    days_until_monday = (7 - now.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7  # If today is Monday, reset is next Monday

    return PremiumPreviewStatus(
        remaining_previews=remaining,
        max_weekly_previews=PremiumPreviewUsage.MAX_WEEKLY_PREVIEWS,
        total_used_lifetime=preview_usage.total_previews_used or 0,
        can_use_preview=remaining > 0,
        resets_in_days=days_until_monday
    )


@router.post("/premium-preview/use", response_model=UsePreviewResponse)
async def use_premium_preview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Use one premium preview.

    Call this when a free user wants to perform a premium-tier search.
    """
    # Premium users don't need previews
    if current_user.is_premium():
        return UsePreviewResponse(
            success=True,
            remaining_previews=999,
            message="You have premium access!"
        )

    # Get or create preview usage record
    preview_usage = db.query(PremiumPreviewUsage).filter(
        PremiumPreviewUsage.user_id == current_user.id
    ).first()

    if not preview_usage:
        preview_usage = PremiumPreviewUsage(user_id=current_user.id)
        db.add(preview_usage)
        db.flush()

    # Try to use a preview
    if preview_usage.use_preview():
        db.commit()
        remaining = preview_usage.get_remaining_previews()

        return UsePreviewResponse(
            success=True,
            remaining_previews=remaining,
            message=f"Premium preview used! {remaining} remaining this week."
        )
    else:
        db.rollback()
        return UsePreviewResponse(
            success=False,
            remaining_previews=0,
            message="No premium previews remaining. Upgrade to unlock unlimited premium searches!"
        )


@router.get("/premium-preview/check")
async def check_premium_or_preview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if user can access premium features (either premium subscriber or has previews).

    Use this before showing premium features to determine if user can access them.
    """
    is_premium = current_user.is_premium()

    if is_premium:
        return {
            "can_access_premium": True,
            "access_type": "subscription",
            "tier": current_user.subscription_tier,
            "remaining_previews": None
        }

    # Check preview availability
    preview_usage = db.query(PremiumPreviewUsage).filter(
        PremiumPreviewUsage.user_id == current_user.id
    ).first()

    if not preview_usage:
        preview_usage = PremiumPreviewUsage(user_id=current_user.id)
        db.add(preview_usage)
        db.commit()

    remaining = preview_usage.get_remaining_previews()
    db.commit()

    return {
        "can_access_premium": remaining > 0,
        "access_type": "preview" if remaining > 0 else "none",
        "tier": "free",
        "remaining_previews": remaining
    }
