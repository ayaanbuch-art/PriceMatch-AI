"""Wardrobe API for managing user's clothing items and outfit suggestions."""
import logging
import json
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from ..database import get_db
from ..models import User, WardrobeItem, Outfit
from ..utils.auth import get_current_user
from ..services.gemini import GeminiService
from ..services.cloudinary_service import CloudinaryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wardrobe", tags=["wardrobe"])


# Pydantic schemas
class WardrobeItemResponse(BaseModel):
    """Wardrobe item response."""
    id: int
    imageUrl: str
    itemType: str
    itemSubtype: Optional[str]
    brand: Optional[str]
    color: Optional[str]
    colors: Optional[List[str]]
    material: Optional[str]
    pattern: Optional[str]
    styleTags: Optional[List[str]]
    season: Optional[str]
    occasions: Optional[List[str]]
    formality: Optional[str]
    name: Optional[str]
    notes: Optional[str]
    timesWorn: int
    isFavorite: bool
    createdAt: datetime

    class Config:
        from_attributes = True


class WardrobeListResponse(BaseModel):
    """Wardrobe list response."""
    items: List[WardrobeItemResponse]
    total: int
    hasMore: bool


class OutfitItemResponse(BaseModel):
    """Simplified item for outfit display."""
    id: int
    imageUrl: str
    itemType: str
    color: Optional[str]


class OutfitResponse(BaseModel):
    """Outfit response."""
    id: int
    name: Optional[str]
    occasion: Optional[str]
    season: Optional[str]
    items: List[OutfitItemResponse]
    isAiSuggested: bool
    aiReasoning: Optional[str]
    isFavorite: bool
    createdAt: datetime


class OutfitSuggestionResponse(BaseModel):
    """AI outfit suggestion response."""
    outfits: List[OutfitResponse]
    message: str


class UpdateItemRequest(BaseModel):
    """Update wardrobe item request."""
    name: Optional[str] = None
    notes: Optional[str] = None
    isFavorite: Optional[bool] = None


def _parse_json_field(value: Optional[str]) -> Optional[List[str]]:
    """Parse JSON string field to list."""
    if not value:
        return None
    try:
        return json.loads(value)
    except:
        return None


def _item_to_response(item: WardrobeItem) -> WardrobeItemResponse:
    """Convert WardrobeItem to response."""
    return WardrobeItemResponse(
        id=item.id,
        imageUrl=item.image_url,
        itemType=item.item_type,
        itemSubtype=item.item_subtype,
        brand=item.brand,
        color=item.color,
        colors=_parse_json_field(item.colors),
        material=item.material,
        pattern=item.pattern,
        styleTags=_parse_json_field(item.style_tags),
        season=item.season,
        occasions=_parse_json_field(item.occasions),
        formality=item.formality,
        name=item.name,
        notes=item.notes,
        timesWorn=item.times_worn or 0,
        isFavorite=item.is_favorite == 1,
        createdAt=item.created_at
    )


@router.post("/items", response_model=WardrobeItemResponse)
async def add_wardrobe_item(
    file: UploadFile = File(...),
    name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add an item to the user's wardrobe.
    Uploads image and uses AI to analyze the item.
    """
    # Rate limit: max 50 wardrobe items for free users
    item_count = db.query(WardrobeItem).filter(
        WardrobeItem.user_id == current_user.id
    ).count()

    max_items = 50 if current_user.subscription_tier == "free" else 500
    if item_count >= max_items:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum {max_items} wardrobe items allowed"
        )

    # Read and validate image
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image too large (max 10MB)"
        )

    # Upload to Cloudinary
    try:
        cloudinary_service = CloudinaryService()
        image_url = cloudinary_service.upload_image(contents, folder="wardrobe")
    except RuntimeError as e:
        # CloudinaryService not configured
        logger.error(f"Cloudinary not configured: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image storage not configured: {str(e)}"
        )
    except Exception as e:
        import traceback
        error_details = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Cloudinary upload failed: {error_details}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image - {error_details}"
        )

    # Analyze with Gemini
    try:
        gemini = GeminiService()
        analysis = await gemini.analyze_wardrobe_item(contents)
    except Exception as e:
        logger.error(f"Gemini analysis failed: {e}")
        # Create item with minimal info if analysis fails
        analysis = {
            "item_type": "unknown",
            "item_subtype": None,
            "brand": None,
            "color": None,
            "colors": [],
            "material": None,
            "pattern": "solid",
            "style_tags": [],
            "season": "all",
            "occasions": ["casual"],
            "formality": "casual"
        }

    # Create wardrobe item
    item = WardrobeItem(
        user_id=current_user.id,
        image_url=image_url,
        item_type=analysis.get("item_type", "unknown"),
        item_subtype=analysis.get("item_subtype"),
        brand=analysis.get("brand"),
        color=analysis.get("color"),
        colors=json.dumps(analysis.get("colors", [])),
        material=analysis.get("material"),
        pattern=analysis.get("pattern"),
        style_tags=json.dumps(analysis.get("style_tags", [])),
        season=analysis.get("season", "all"),
        occasions=json.dumps(analysis.get("occasions", [])),
        formality=analysis.get("formality", "casual"),
        name=name
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    logger.info(f"User {current_user.id} added wardrobe item: {item.id}")

    return _item_to_response(item)


@router.get("/items", response_model=WardrobeListResponse)
async def get_wardrobe_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    item_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's wardrobe items."""
    query = db.query(WardrobeItem).filter(WardrobeItem.user_id == current_user.id)

    if item_type:
        query = query.filter(WardrobeItem.item_type == item_type)

    total = query.count()
    items = query.order_by(desc(WardrobeItem.created_at)).offset(skip).limit(limit).all()

    return WardrobeListResponse(
        items=[_item_to_response(item) for item in items],
        total=total,
        hasMore=(skip + limit) < total
    )


@router.get("/items/{item_id}", response_model=WardrobeItemResponse)
async def get_wardrobe_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific wardrobe item."""
    item = db.query(WardrobeItem).filter(
        WardrobeItem.id == item_id,
        WardrobeItem.user_id == current_user.id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return _item_to_response(item)


@router.patch("/items/{item_id}", response_model=WardrobeItemResponse)
async def update_wardrobe_item(
    item_id: int,
    request: UpdateItemRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a wardrobe item."""
    item = db.query(WardrobeItem).filter(
        WardrobeItem.id == item_id,
        WardrobeItem.user_id == current_user.id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if request.name is not None:
        item.name = request.name[:100] if request.name else None
    if request.notes is not None:
        item.notes = request.notes[:500] if request.notes else None
    if request.isFavorite is not None:
        item.is_favorite = 1 if request.isFavorite else 0

    db.commit()
    db.refresh(item)

    return _item_to_response(item)


@router.delete("/items/{item_id}")
async def delete_wardrobe_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a wardrobe item."""
    item = db.query(WardrobeItem).filter(
        WardrobeItem.id == item_id,
        WardrobeItem.user_id == current_user.id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()

    return {"message": "Item deleted"}


@router.post("/suggest-outfits", response_model=OutfitSuggestionResponse)
async def suggest_outfits(
    occasion: Optional[str] = None,
    season: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI-suggested outfits based on user's wardrobe.
    """
    # Get user's wardrobe items
    items = db.query(WardrobeItem).filter(
        WardrobeItem.user_id == current_user.id
    ).all()

    if len(items) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add at least 2 items to your wardrobe to get outfit suggestions"
        )

    # Prepare wardrobe summary for AI
    wardrobe_summary = []
    for item in items:
        wardrobe_summary.append({
            "id": item.id,
            "type": item.item_type,
            "subtype": item.item_subtype,
            "color": item.color,
            "pattern": item.pattern,
            "style": _parse_json_field(item.style_tags),
            "formality": item.formality,
            "season": item.season
        })

    # Get AI suggestions
    try:
        gemini = GeminiService()
        suggestions = await gemini.suggest_outfits(
            wardrobe_items=wardrobe_summary,
            occasion=occasion,
            season=season
        )
    except Exception as e:
        logger.error(f"Outfit suggestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate outfit suggestions"
        )

    # Build response with actual item data
    outfits = []
    for idx, suggestion in enumerate(suggestions.get("outfits", [])[:5]):
        item_ids = suggestion.get("item_ids", [])
        outfit_items = [item for item in items if item.id in item_ids]

        if len(outfit_items) >= 2:
            outfits.append(OutfitResponse(
                id=idx + 1,  # Temporary ID for unsaved suggestions
                name=suggestion.get("name", f"Outfit {idx + 1}"),
                occasion=suggestion.get("occasion", occasion),
                season=suggestion.get("season", season),
                items=[
                    OutfitItemResponse(
                        id=item.id,
                        imageUrl=item.image_url,
                        itemType=item.item_type,
                        color=item.color
                    ) for item in outfit_items
                ],
                isAiSuggested=True,
                aiReasoning=suggestion.get("reasoning"),
                isFavorite=False,
                createdAt=datetime.utcnow()
            ))

    return OutfitSuggestionResponse(
        outfits=outfits,
        message=f"Found {len(outfits)} outfit suggestions" if outfits else "Couldn't create outfits with current wardrobe"
    )


@router.get("/stats")
async def get_wardrobe_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get wardrobe statistics."""
    items = db.query(WardrobeItem).filter(
        WardrobeItem.user_id == current_user.id
    ).all()

    # Count by type
    type_counts = {}
    color_counts = {}
    for item in items:
        type_counts[item.item_type] = type_counts.get(item.item_type, 0) + 1
        if item.color:
            color_counts[item.color] = color_counts.get(item.color, 0) + 1

    return {
        "totalItems": len(items),
        "byType": type_counts,
        "topColors": sorted(color_counts.items(), key=lambda x: x[1], reverse=True)[:5],
        "favorites": sum(1 for item in items if item.is_favorite == 1)
    }
