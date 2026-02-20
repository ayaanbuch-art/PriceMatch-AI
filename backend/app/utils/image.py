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

# Secure upload directory (absolute path)
UPLOAD_DIR = os.path.abspath("static/uploads")

# Valid UUID filename pattern (prevents path traversal)
UUID_FILENAME_PATTERN = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\.jpg$')


async def save_image_locally(file: UploadFile) -> str:
    """
    Process an uploaded image and save locally.
    Returns the local URL path of the uploaded image.
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
