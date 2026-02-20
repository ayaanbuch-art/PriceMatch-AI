"""Visual search API endpoints with secure input validation."""
import logging
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import User, SearchHistory, UserInteraction
from ..schemas import SearchResult, SearchHistoryResponse
from ..utils.auth import get_current_user
from ..utils.image import save_image_locally
from ..utils.validators import SecureSearchParams, SecureImageUpload
from ..services.gemini import gemini_service
from ..services.product_search import product_search_service
from ..services.recommendations import recommendation_service
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


async def check_search_limit(user: User, db: Session):
    """Check if user has reached their monthly search limit based on tier."""
    if not user.can_perform_scan():
        limit = user.get_monthly_scan_limit()
        raise HTTPException(
            status_code=429,
            detail=f"Monthly scan limit reached ({limit} scans). Upgrade your plan for more scans."
        )


@router.post("/image", response_model=SearchResult)
async def search_by_image(
    file: UploadFile = File(...),
    gender: Optional[str] = Form("either"),
    search_mode: Optional[str] = Form("alternatives"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload an image and search for similar products.
    Returns AI analysis and product matches.

    Args:
        file: Image file (JPEG, PNG, GIF, WebP - max 10MB)
        gender: Filter results by 'male', 'female', or 'either'
        search_mode: 'exact' to find the same item, 'alternatives' for similar/cheaper options
    """
    try:
        # Validate search parameters
        params = SecureSearchParams(gender=gender, search_mode=search_mode)

        # Check search limit
        await check_search_limit(current_user, db)

        # Validate file content type
        if not file.content_type or not SecureImageUpload.validate_content_type(file.content_type):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Supported: JPEG, PNG, GIF, WebP"
            )

        # Read and validate file size and magic bytes
        contents = await file.read()
        await file.seek(0)  # Reset for later processing

        if len(contents) > SecureImageUpload.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail="File too large. Maximum size is 10MB"
            )

        if not SecureImageUpload.validate_magic_bytes(contents):
            raise HTTPException(
                status_code=400,
                detail="Invalid file content. File must be a valid image"
            )

        # Process and save image locally
        local_image_path = await save_image_locally(file)

        # Get user's subscription tier for enhanced AI
        user_tier = current_user.subscription_tier or "free"
        tier_features = gemini_service.get_tier_features(user_tier)

        # Analyze image with Gemini Vision
        analysis = await gemini_service.analyze_image(
            local_image_path,
            tier=user_tier,
            search_mode=params.search_mode or "alternatives"
        )

        # Search for products with gender filter
        products = await product_search_service.search_products(
            analysis,
            gender=params.gender or "either",
            tier=user_tier,
            search_mode=params.search_mode or "alternatives"
        )

        # Construct full URL for client/database
        full_image_url = f"{settings.BASE_URL}{local_image_path}"

        # Save to search history
        search_record = SearchHistory(
            user_id=current_user.id,
            image_url=full_image_url,
            search_query=" ".join(analysis.search_terms),
            gemini_analysis=analysis.dict(),
            results_data=[p.dict() for p in products],
            search_type=analysis.item_type
        )
        db.add(search_record)
        db.commit()
        db.refresh(search_record)

        # Track interaction
        interaction = UserInteraction(
            user_id=current_user.id,
            product_id=f"search_{search_record.id}",
            product_category=analysis.item_type,
            interaction_type="search"
        )
        db.add(interaction)

        # Increment monthly scan count for the user
        current_user.increment_scan_count()
        db.commit()

        # Invalidate recommendation cache so "For You" reflects this new search
        recommendation_service.invalidate_user_recommendations(current_user.id)

        logger.info(f"Search completed: user_id={current_user.id}, search_id={search_record.id}")

        return SearchResult(
            id=search_record.id,
            image_url=full_image_url,
            analysis=analysis,
            products=products,
            created_at=search_record.created_at
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Generate error ID for support tracking
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"Search error [error_id={error_id}]: {type(e).__name__}", exc_info=True)

        # Return sanitized error to client
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred processing your request. Error ID: {error_id}"
        )


@router.get("/history", response_model=SearchHistoryResponse)
async def get_search_history(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's search history with pagination."""

    # Validate pagination parameters
    if skip < 0:
        skip = 0
    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100

    total = db.query(SearchHistory).filter(
        SearchHistory.user_id == current_user.id
    ).count()

    searches = db.query(SearchHistory).filter(
        SearchHistory.user_id == current_user.id
    ).order_by(SearchHistory.created_at.desc()).offset(skip).limit(limit).all()

    search_results = []
    for search in searches:
        from ..schemas import GeminiAnalysis, Product

        analysis = GeminiAnalysis(**search.gemini_analysis)
        products = [Product(**p) for p in search.results_data] if search.results_data else []

        search_results.append(SearchResult(
            id=search.id,
            image_url=search.image_url,
            analysis=analysis,
            products=products,
            created_at=search.created_at
        ))

    return SearchHistoryResponse(searches=search_results, total=total)


@router.get("/{search_id}", response_model=SearchResult)
async def get_search_by_id(
    search_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific search result by ID (user must own the search)."""

    # Validate search_id
    if search_id < 1:
        raise HTTPException(status_code=400, detail="Invalid search ID")

    search = db.query(SearchHistory).filter(
        SearchHistory.id == search_id,
        SearchHistory.user_id == current_user.id  # Authorization check
    ).first()

    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    from ..schemas import GeminiAnalysis, Product

    analysis = GeminiAnalysis(**search.gemini_analysis)
    products = [Product(**p) for p in search.results_data] if search.results_data else []

    return SearchResult(
        id=search.id,
        image_url=search.image_url,
        analysis=analysis,
        products=products,
        created_at=search.created_at
    )


@router.delete("/history/all")
async def clear_all_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear all search history for the current user."""
    deleted_count = db.query(SearchHistory).filter(
        SearchHistory.user_id == current_user.id
    ).delete()

    db.commit()

    logger.info(f"Cleared search history: user_id={current_user.id}, count={deleted_count}")

    return {
        "message": f"Successfully deleted {deleted_count} searches",
        "deleted_count": deleted_count
    }


@router.delete("/{search_id}")
async def delete_search(
    search_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a search from history (user must own the search)."""

    if search_id < 1:
        raise HTTPException(status_code=400, detail="Invalid search ID")

    search = db.query(SearchHistory).filter(
        SearchHistory.id == search_id,
        SearchHistory.user_id == current_user.id  # Authorization check
    ).first()

    if not search:
        raise HTTPException(status_code=404, detail="Search not found")

    db.delete(search)
    db.commit()

    logger.info(f"Deleted search: user_id={current_user.id}, search_id={search_id}")

    return {"message": "Search deleted successfully"}


@router.post("/text", response_model=SearchResult)
async def search_by_text(
    query: str = Form(...),
    gender: Optional[str] = Form("either"),
    search_mode: Optional[str] = Form("alternatives"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search for products by text description.
    Uses AI to understand the query and find matching products.

    Args:
        query: Text description of the item to find (e.g., "black leather jacket", "wireless earbuds")
        gender: Filter results by 'male', 'female', or 'either'
        search_mode: 'exact' to find specific item, 'alternatives' for similar/cheaper options
    """
    try:
        # Validate query
        if not query or len(query.strip()) < 3:
            raise HTTPException(
                status_code=400,
                detail="Search query must be at least 3 characters"
            )

        if len(query) > 500:
            raise HTTPException(
                status_code=400,
                detail="Search query is too long (max 500 characters)"
            )

        # Validate search parameters
        params = SecureSearchParams(gender=gender, search_mode=search_mode)

        # Check search limit
        await check_search_limit(current_user, db)

        # Get user's subscription tier
        user_tier = current_user.subscription_tier or "free"

        # Analyze text query with Gemini
        analysis = await gemini_service.analyze_text_query(
            query=query.strip(),
            tier=user_tier,
            search_mode=params.search_mode or "alternatives"
        )

        # Search for products with gender filter
        products = await product_search_service.search_products(
            analysis,
            gender=params.gender or "either",
            tier=user_tier,
            search_mode=params.search_mode or "alternatives"
        )

        # Save to search history (no image for text search)
        search_record = SearchHistory(
            user_id=current_user.id,
            image_url=None,  # No image for text search
            search_query=query.strip(),
            gemini_analysis=analysis.dict(),
            results_data=[p.dict() for p in products],
            search_type=analysis.item_type
        )
        db.add(search_record)
        db.commit()
        db.refresh(search_record)

        # Track interaction
        interaction = UserInteraction(
            user_id=current_user.id,
            product_id=f"text_search_{search_record.id}",
            product_category=analysis.item_type,
            interaction_type="text_search"
        )
        db.add(interaction)

        # Increment monthly scan count
        current_user.increment_scan_count()
        db.commit()

        # Invalidate recommendation cache so "For You" reflects this new search
        recommendation_service.invalidate_user_recommendations(current_user.id)

        logger.info(f"Text search completed: user_id={current_user.id}, search_id={search_record.id}, query='{query[:50]}'")

        return SearchResult(
            id=search_record.id,
            image_url=None,
            analysis=analysis,
            products=products,
            created_at=search_record.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"Text search error [error_id={error_id}]: {type(e).__name__}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred processing your request. Error ID: {error_id}"
        )


@router.get("/ai-info")
async def get_ai_info():
    """
    Get AI disclaimer and tips for better search results.
    No authentication required - this is public info for the app UI.
    """
    return gemini_service.get_ai_disclaimer()
