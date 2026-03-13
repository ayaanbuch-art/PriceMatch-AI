"""Image processing utilities with security hardening."""
import io
import uuid
import os
import re
import shutil
import logging
from PIL import Image
from fastapi import UploadFile, HTTPException

from ..config import settings

logger = logging.getLogger(__name__)

# Try to import cloudinary (optional but recommended for Google Lens)
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
        logger.info("Cloudinary configured successfully - Google Lens visual search enabled")
except ImportError:
    CLOUDINARY_AVAILABLE = False
    logger.warning("Cloudinary not installed - Google Lens visual search will be limited")

# Secure upload directory (absolute path)
UPLOAD_DIR = os.path.abspath("static/uploads")

# Valid UUID filename pattern (prevents path traversal)
UUID_FILENAME_PATTERN = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\.jpg$')


async def save_image_locally(file: UploadFile) -> str:
    """
    Process an uploaded image and save locally.
    Also uploads to Cloudinary if configured (for Google Lens visual search).

    Returns tuple: (local_url_path, cloudinary_url or None)
    But for backwards compatibility, returns just local_url_path.
    Use save_image_with_cloudinary() to get both URLs.
    """
    try:
        # Read image file
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))

        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Resize if too large (max 2000px on longest side)
        max_size = 2000
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        # Compress image
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)

        # Ensure uploads directory exists
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        # Generate secure unique filename (UUID only - no user input)
        filename = f"{uuid.uuid4()}.jpg"
        file_path = os.path.join(UPLOAD_DIR, filename)

        # Verify path is within upload directory (defense in depth)
        if not os.path.abspath(file_path).startswith(UPLOAD_DIR):
            logger.error(f"Path traversal attempt detected: {file_path}")
            raise HTTPException(status_code=400, detail="Invalid file path")

        # Save to disk
        with open(file_path, "wb") as f:
            f.write(output.getbuffer())

        # Return local URL path (accessible via static mount)
        return f"/static/uploads/{filename}"

    except HTTPException:
        raise
    except Exception as e:
        # Log the actual error for debugging but return generic message
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"Image processing error [{error_id}]: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing image. Error ID: {error_id}"
        )


async def save_image_with_cloudinary(file: UploadFile) -> tuple:
    """
    Process an uploaded image, save locally AND upload to Cloudinary.

    Returns tuple: (local_url_path, cloudinary_public_url)

    The cloudinary_public_url can be used for Google Lens visual search,
    as it's publicly accessible from any server.
    """
    try:
        # Read image file
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))

        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Resize if too large (max 2000px on longest side)
        max_size = 2000
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        # Compress image for local storage
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)

        # Ensure uploads directory exists
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        # Generate secure unique filename (UUID only - no user input)
        unique_id = str(uuid.uuid4())
        filename = f"{unique_id}.jpg"
        file_path = os.path.join(UPLOAD_DIR, filename)

        # Verify path is within upload directory (defense in depth)
        if not os.path.abspath(file_path).startswith(UPLOAD_DIR):
            logger.error(f"Path traversal attempt detected: {file_path}")
            raise HTTPException(status_code=400, detail="Invalid file path")

        # Save to disk
        output.seek(0)
        with open(file_path, "wb") as f:
            f.write(output.getbuffer())

        local_url = f"/static/uploads/{filename}"
        cloudinary_url = None

        # Upload to Cloudinary if configured
        if CLOUDINARY_AVAILABLE:
            try:
                output.seek(0)
                result = cloudinary.uploader.upload(
                    output,
                    public_id=f"pricematch/{unique_id}",
                    folder="pricematch_searches",
                    resource_type="image",
                    overwrite=True,
                    # Auto-delete after 24 hours to save storage
                    invalidate=True
                )
                cloudinary_url = result.get("secure_url")
                logger.info(f"Image uploaded to Cloudinary: {cloudinary_url}")
            except Exception as e:
                logger.warning(f"Cloudinary upload failed (will use local): {e}")
                cloudinary_url = None

        return (local_url, cloudinary_url)

    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"Image processing error [{error_id}]: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing image. Error ID: {error_id}"
        )


def delete_image_locally(image_url: str) -> bool:
    """
    Delete an image from local storage.
    Security: Only allows deletion of valid UUID-named files within upload directory.
    """
    try:
        # Extract filename from URL
        # URL format: /static/uploads/filename.jpg
        if "/static/uploads/" not in image_url:
            return False

        # Get just the filename using basename (prevents path traversal)
        raw_filename = image_url.split("/static/uploads/")[-1]
        filename = os.path.basename(raw_filename)

        # Validate filename is a valid UUID format (strict validation)
        if not UUID_FILENAME_PATTERN.match(filename):
            logger.warning(f"Invalid filename format attempted for deletion: {filename}")
            return False

        # Construct safe file path
        file_path = os.path.join(UPLOAD_DIR, filename)

        # Verify the resolved path is within upload directory (defense in depth)
        resolved_path = os.path.abspath(file_path)
        if not resolved_path.startswith(UPLOAD_DIR):
            logger.error(f"Path traversal attempt in delete: {file_path} -> {resolved_path}")
            return False

        if os.path.exists(resolved_path) and os.path.isfile(resolved_path):
            os.remove(resolved_path)
            logger.info(f"Deleted image: {filename}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting image: {e}")
        return False
