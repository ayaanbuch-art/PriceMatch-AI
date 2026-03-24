"""Cloudinary service for image uploads."""
import base64
import logging
import uuid
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)

# Try to import cloudinary at module level
try:
    import cloudinary
    import cloudinary.uploader
    CLOUDINARY_IMPORTED = True
except ImportError:
    CLOUDINARY_IMPORTED = False
    cloudinary = None
    logger.warning("Cloudinary package not installed")


class CloudinaryService:
    """Service for uploading images to Cloudinary."""

    _configured = False

    def __init__(self):
        # Check and configure at instantiation time (not module load time)
        # This ensures Railway environment variables are available
        if not CLOUDINARY_IMPORTED:
            raise RuntimeError("Cloudinary package is not installed")

        # Re-read settings at instantiation time
        cloud_name = settings.CLOUDINARY_CLOUD_NAME
        api_key = settings.CLOUDINARY_API_KEY
        api_secret = settings.CLOUDINARY_API_SECRET

        logger.info(f"Cloudinary init check: cloud_name={bool(cloud_name)}, api_key={bool(api_key)}, api_secret={bool(api_secret)}")

        if not cloud_name or not api_key or not api_secret:
            raise RuntimeError(
                f"Cloudinary is not configured. "
                f"cloud_name={'set' if cloud_name else 'MISSING'}, "
                f"api_key={'set' if api_key else 'MISSING'}, "
                f"api_secret={'set' if api_secret else 'MISSING'}. "
                f"Please set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET environment variables."
            )

        # Configure cloudinary
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        logger.info(f"Cloudinary configured for cloud: {cloud_name}")

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
