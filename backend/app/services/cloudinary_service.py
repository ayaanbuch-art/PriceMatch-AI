"""Cloudinary service for image uploads."""
import base64
import logging
import uuid
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)

# Try to import cloudinary
try:
    import cloudinary
    import cloudinary.uploader
    CLOUDINARY_AVAILABLE = bool(
        settings.CLOUDINARY_CLOUD_NAME and
        settings.CLOUDINARY_API_KEY and
        settings.CLOUDINARY_API_SECRET
    )
    if CLOUDINARY_AVAILABLE:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )
        logger.info(f"Cloudinary configured for cloud: {settings.CLOUDINARY_CLOUD_NAME}")
    else:
        logger.warning(f"Cloudinary not fully configured: cloud_name={bool(settings.CLOUDINARY_CLOUD_NAME)}, api_key={bool(settings.CLOUDINARY_API_KEY)}, api_secret={bool(settings.CLOUDINARY_API_SECRET)}")
except ImportError:
    CLOUDINARY_AVAILABLE = False
    cloudinary = None
    logger.warning("Cloudinary not installed")


class CloudinaryService:
    """Service for uploading images to Cloudinary."""

    def __init__(self):
        if not CLOUDINARY_AVAILABLE:
            raise RuntimeError(
                "Cloudinary is not configured. Please set CLOUDINARY_CLOUD_NAME, "
                "CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET environment variables."
            )

    def upload_image(self, image_data: bytes, folder: str = "uploads", public_id: Optional[str] = None) -> str:
        """
        Upload an image to Cloudinary using base64 data URI.

        Args:
            image_data: Raw image bytes
            folder: Cloudinary folder to upload to
            public_id: Optional custom public ID

        Returns:
            The secure URL of the uploaded image
        """
        unique_id = public_id or str(uuid.uuid4())

        # Convert to base64 data URI (more reliable than BytesIO)
        base64_data = base64.b64encode(image_data).decode('utf-8')
        data_uri = f"data:image/jpeg;base64,{base64_data}"

        logger.info(f"Uploading image to Cloudinary, size: {len(image_data)} bytes")

        result = cloudinary.uploader.upload(
            data_uri,
            public_id=f"{folder}/{unique_id}",
            folder=f"pricematch_{folder}",
            resource_type="image",
            overwrite=True
        )

        url = result.get("secure_url")
        if not url:
            raise ValueError(f"No URL returned from Cloudinary. Response: {result}")

        logger.info(f"Image uploaded to Cloudinary: {url}")
        return url

    def delete_image(self, public_id: str) -> bool:
        """
        Delete an image from Cloudinary.

        Args:
            public_id: The public ID of the image

        Returns:
            True if deleted successfully
        """
        try:
            result = cloudinary.uploader.destroy(public_id)
            return result.get("result") == "ok"
        except Exception as e:
            logger.error(f"Cloudinary delete failed: {e}")
            return False
