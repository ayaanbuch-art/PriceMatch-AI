"""User data management API endpoints (GDPR compliance)."""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from ..database import get_db
from ..models import User
from ..models.search_history import SearchHistory
from ..models.favorite import Favorite
from ..models.gamification import UserStreak, UserAchievement
from ..utils.auth import get_current_user
from ..utils.audit import audit_log, AuditAction, get_client_info

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user", tags=["user"])


# Response models
class UserExportData(BaseModel):
    email: Optional[str]
    full_name: Optional[str]
    created_at: Optional[str]
    tier: Optional[str]


class SearchExportData(BaseModel):
    query: Optional[str]
    search_type: Optional[str]
    created_at: Optional[str]


class FavoriteExportData(BaseModel):
    product_id: str
    product_title: Optional[str]
    created_at: Optional[str]


class UserDataExport(BaseModel):
    user: UserExportData
    searches: Optional[List[SearchExportData]]
    favorites: Optional[List[FavoriteExportData]]
    exported_at: str


class DeleteAccountResponse(BaseModel):
    success: bool
    message: str


@router.get("/data-export", response_model=UserDataExport)
async def export_user_data(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export all user data (GDPR Article 20 - Right to data portability).
    Returns all data associated with the user's account.
    """
    client_info = get_client_info(request)

    try:
        # Get user's search history
        searches = db.query(SearchHistory).filter(
            SearchHistory.user_id == current_user.id
        ).order_by(SearchHistory.created_at.desc()).all()

        search_data = []
        for search in searches:
            search_data.append(SearchExportData(
                query=search.query if hasattr(search, 'query') else None,
                search_type=search.search_type if hasattr(search, 'search_type') else "image",
                created_at=search.created_at.isoformat() if search.created_at else None
            ))

        # Get user's favorites
        favorites = db.query(Favorite).filter(
            Favorite.user_id == current_user.id
        ).order_by(Favorite.created_at.desc()).all()

        favorite_data = []
        for fav in favorites:
            product_title = None
            if fav.product_data and isinstance(fav.product_data, dict):
                product_title = fav.product_data.get('title')
            favorite_data.append(FavoriteExportData(
                product_id=fav.product_id,
                product_title=product_title,
                created_at=fav.created_at.isoformat() if fav.created_at else None
            ))

        # Build export
        export = UserDataExport(
            user=UserExportData(
                email=current_user.email,
                full_name=current_user.full_name,
                created_at=current_user.created_at.isoformat() if current_user.created_at else None,
                tier=current_user.subscription_tier
            ),
            searches=search_data,
            favorites=favorite_data,
            exported_at=datetime.utcnow().isoformat()
        )

        audit_log(
            AuditAction.DATA_EXPORT,
            user_id=current_user.id,
            email=current_user.email,
            success=True,
            **client_info
        )

        return export

    except Exception as e:
        logger.error(f"Data export failed for user {current_user.id}: {str(e)}")
        audit_log(
            AuditAction.DATA_EXPORT,
            user_id=current_user.id,
            email=current_user.email,
            success=False,
            error_message=str(e),
            **client_info
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export user data"
        )


@router.delete("/account", response_model=DeleteAccountResponse)
async def delete_account(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete user account and all associated data (GDPR Article 17 - Right to erasure).
    This action is irreversible.
    """
    client_info = get_client_info(request)
    user_id = current_user.id
    user_email = current_user.email

    try:
        # Delete search history
        db.query(SearchHistory).filter(
            SearchHistory.user_id == user_id
        ).delete(synchronize_session=False)

        # Delete favorites
        db.query(Favorite).filter(
            Favorite.user_id == user_id
        ).delete(synchronize_session=False)

        # Delete gamification data
        try:
            db.query(UserStreak).filter(
                UserStreak.user_id == user_id
            ).delete(synchronize_session=False)

            db.query(UserAchievement).filter(
                UserAchievement.user_id == user_id
            ).delete(synchronize_session=False)
        except Exception as e:
            # Gamification tables might not exist in all setups
            logger.warning(f"Could not delete gamification data: {str(e)}")

        # Delete the user account
        db.delete(current_user)
        db.commit()

        audit_log(
            AuditAction.ACCOUNT_DELETED,
            user_id=user_id,
            email=user_email,
            success=True,
            **client_info
        )

        logger.info(f"Account deleted successfully for user {user_id}")

        return DeleteAccountResponse(
            success=True,
            message="Your account and all associated data have been permanently deleted."
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Account deletion failed for user {user_id}: {str(e)}")
        audit_log(
            AuditAction.ACCOUNT_DELETED,
            user_id=user_id,
            email=user_email,
            success=False,
            error_message=str(e),
            **client_info
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}"
        )
