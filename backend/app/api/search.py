"""Visual search API endpoints with secure input validation."""
import logging
import uuid
import hashlib
import json
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import User, SearchHistory, UserInteraction
from ..schemas import SearchResult, SearchHistoryResponse, GeminiAnalysis, Product
from ..utils.auth import get_current_user
from ..utils.image import save_image_locally, save_image_with_cloudinary
from ..utils.validators import SecureSearchParams, SecureImageUpload
from ..services.gemini import gemini_service
from ..services.product_search import product_search_service
from ..services.recommendations import recommendation_service
from ..services.redis_cache import redis_cache
from ..config import settings

logger = logging.getLogger(__name__)


def compute_image_hash(image_bytes: bytes) -> str:
    """Compute a hash of image content for caching.

    This allows us to cache results based on actual image content,
    not the URL. Same image = same hash = cache hit.
    """
    return hashlib.sha256(image_bytes).hexdigest()[:32]


async def get_cached_search(image_hash: str, search_mode: str, gender: str):
    """Check Redis for cached search results by image hash."""
    if not redis_cache._connected:
        return None

    cache_key = f"imgsearch:{image_hash}:{search_mode}:{gender}"
    try:
        cached = await redis_cache._redis_client.get(cache_key)
        if cached:
            data = json.loads(cached)
            logger.warning(f"CACHE HIT! Returning cached results for image {image_hash[:8]}...")
            return data
    except Exception as e:
        logger.warning(f"Cache get error: {e}")
    return None


async def cache_search_result(image_hash: str, search_mode: str, gender: str,
                              analysis_dict: dict, products_list: list):
    """Cache search results by image hash. TTL = 24 hours."""
    if not redis_cache._connected:
        return

    cache_key = f"imgsearch:{image_hash}:{search_mode}:{gender}"
    try:
        data = {
            "analysis": analysis_dict,
            "products": products_list
        }
        await redis_cache._redis_client.setex(
            cache_key,
            86400,  # 24 hour TTL
            json.dumps(data)
        )
        logger.info(f"Cached search results for image {image_hash[:8]}...")
    except Exception as e:
        logger.warning(f"Cache set error: {e}")

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
    search_mode: Optional[str] = Form("exact"),
    user_brand: Optional[str] = Form(None),
    user_price: Optional[str] = Form(None),
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
        user_brand: Optional brand name provided by user for better accuracy
        user_price: Optional price estimate provided by user
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

        # Compute image hash for caching (based on actual image content)
        image_hash = compute_image_hash(contents)
        logger.info(f"Image hash: {image_hash[:8]}...")

        # Check cache first - if we've seen this exact image before, return cached results
        # This saves ALL API costs (Gemini + Google Lens + SerpAPI)
        cached_result = await get_cached_search(
            image_hash,
            params.search_mode or "exact",
            params.gender or "either"
        )

        if cached_result:
            # Cache hit! Skip all API calls and return cached results
            analysis = GeminiAnalysis(**cached_result["analysis"])
            products = [Product(**p) for p in cached_result["products"]]

            # Still save to search history (but mark as cached)
            search_record = SearchHistory(
                user_id=current_user.id,
                image_url="[cached]",
                search_query=" ".join(analysis.search_terms),
                gemini_analysis=cached_result["analysis"],
                results_data=cached_result["products"],
                search_type=analysis.item_type
            )
            db.add(search_record)

            # Track interaction
            interaction = UserInteraction(
                user_id=current_user.id,
                product_id=f"search_cached_{image_hash[:8]}",
                product_category=analysis.item_type,
                interaction_type="search"
            )
            db.add(interaction)

            # Still count towards scan limit
            current_user.increment_scan_count()
            db.commit()
            db.refresh(search_record)

            logger.warning(f"CACHE HIT - Saved API costs! Returning {len(products)} cached products")

            return SearchResult(
                id=search_record.id,
                image_url="[cached]",
                analysis=analysis,
                products=products,
                created_at=search_record.created_at
            )

        # Cache miss - proceed with normal flow (will cache results at the end)
        logger.info("Cache miss - calling APIs...")

        # Process and save image (local + Cloudinary for Google Lens)
        local_image_path, cloudinary_url = await save_image_with_cloudinary(file)

        # Construct full URL for client/database
        full_image_url = f"{settings.BASE_URL}{local_image_path}"

        # For Google Lens visual search, prefer Cloudinary URL (publicly accessible)
        # Fall back to full_image_url if Cloudinary not configured
        lens_image_url = cloudinary_url if cloudinary_url else full_image_url
        if cloudinary_url:
            logger.info(f"Using Cloudinary URL for Google Lens: {cloudinary_url}")
        else:
            logger.warning("Cloudinary not configured - Google Lens may not work with local URLs")

        # Get user's subscription tier for enhanced AI
        user_tier = current_user.subscription_tier or "free"
        tier_features = gemini_service.get_tier_features(user_tier)

        # Analyze image with Gemini Vision
        analysis = await gemini_service.analyze_image(
            local_image_path,
            tier=user_tier,
            search_mode=params.search_mode or "exact"
        )

        # Override AI analysis with user-provided values for better accuracy
        if user_brand and user_brand.strip():
            analysis.brand = user_brand.strip()
            logger.info(f"Using user-provided brand: '{analysis.brand}'")

        if user_price and user_price.strip():
            analysis.price_estimate = user_price.strip()
            logger.info(f"Using user-provided price: '{analysis.price_estimate}'")

        # Search for products using BOTH Google Lens (visual) AND Google Shopping (text)
        # Pass Cloudinary image_url to enable visual matching via Google Lens API
        # Pass user-provided brand/price for improved accuracy
        # Pass user's size preferences for filtering
        products = await product_search_service.search_products(
            analysis,
            gender=params.gender or "either",
            tier=user_tier,
            search_mode=params.search_mode or "exact",
            image_url=lens_image_url,  # Cloudinary URL for Google Lens visual search
            user_brand=user_brand,  # User-provided brand for better accuracy
            user_price=user_price,  # User-provided price estimate
            user_sizes=current_user.preferred_sizes  # User's size preferences for filtering
        )

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

        # Cache the results for future identical image uploads
        # This saves ALL API costs on repeat searches
        await cache_search_result(
            image_hash,
            params.search_mode or "exact",
            params.gender or "either",
            analysis.dict(),
            [p.dict() for p in products]
        )

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
    search_mode: Optional[str] = Form("exact"),
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
            search_mode=params.search_mode or "exact"
        )

        # Search for products with gender filter and size preferences
        products = await product_search_service.search_products(
            analysis,
            gender=params.gender or "either",
            tier=user_tier,
            search_mode=params.search_mode or "exact",
            user_sizes=current_user.preferred_sizes  # User's size preferences
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
