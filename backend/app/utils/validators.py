"""Input validation utilities using Pydantic for strict server-side validation."""
import re
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator
from fastapi import HTTPException
import html


# Constants for validation
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
NAME_MAX_LENGTH = 100
SEARCH_QUERY_MAX_LENGTH = 500

# Disallowed patterns for XSS/SQLi prevention
DANGEROUS_PATTERNS = [
    r'<script',
    r'javascript:',
    r'on\w+\s*=',
    r'--',
    r';.*;',
    r'UNION\s+SELECT',
    r'DROP\s+TABLE',
    r'INSERT\s+INTO',
    r'DELETE\s+FROM',
    r'UPDATE\s+.*\s+SET',
    r'<iframe',
    r'<object',
    r'<embed',
]

DANGEROUS_REGEX = re.compile('|'.join(DANGEROUS_PATTERNS), re.IGNORECASE)


def sanitize_string(value: str) -> str:
    """
    Sanitize a string to prevent XSS attacks.
    HTML-encodes dangerous characters.
    """
    if not value:
        return value
    # HTML escape to prevent XSS
    return html.escape(value.strip())


def check_dangerous_patterns(value: str, field_name: str = "input") -> None:
    """
    Check for SQL injection and XSS patterns.
    Raises HTTPException if dangerous patterns found.
    """
    if DANGEROUS_REGEX.search(value):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid characters detected in {field_name}"
        )


class SecureUserCreate(BaseModel):
    """Secure user registration with strict validation."""
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    full_name: Optional[str] = Field(None, max_length=NAME_MAX_LENGTH)

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v):
            raise ValueError('Invalid email format')
        check_dangerous_patterns(v, "email")
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        # Check password complexity
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v

    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = sanitize_string(v)
        check_dangerous_patterns(v, "name")
        # Only allow alphanumeric, spaces, hyphens, apostrophes
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", v):
            raise ValueError('Name contains invalid characters')
        return v


class SecureUserLogin(BaseModel):
    """Secure login with validation."""
    email: str = Field(..., max_length=255)
    password: str = Field(..., max_length=PASSWORD_MAX_LENGTH)

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v):
            raise ValueError('Invalid email format')
        return v


class SecureAppleSignIn(BaseModel):
    """Secure Apple Sign-In validation."""
    user_id: str = Field(..., min_length=1, max_length=255)
    identity_token: str = Field(..., min_length=1)
    email: Optional[str] = Field(None, max_length=255)
    full_name: Optional[str] = Field(None, max_length=NAME_MAX_LENGTH)

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        v = v.strip()
        # Apple user IDs are alphanumeric with dots
        if not re.match(r'^[a-zA-Z0-9\.]+$', v):
            raise ValueError('Invalid Apple user ID format')
        return v

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v):
            raise ValueError('Invalid email format')
        return v

    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return sanitize_string(v)


class SecureSearchParams(BaseModel):
    """Secure search parameters validation."""
    gender: Optional[str] = Field("either", pattern=r'^(male|female|either)$')
    search_mode: Optional[str] = Field("alternatives", pattern=r'^(exact|alternatives)$')

    @field_validator('gender', 'search_mode')
    @classmethod
    def validate_enum(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.lower().strip()
        return v


class SecureImageUpload:
    """Validation for image uploads."""
    ALLOWED_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    @staticmethod
    def validate_content_type(content_type: str) -> bool:
        """Validate MIME type."""
        return content_type.lower() in SecureImageUpload.ALLOWED_CONTENT_TYPES

    @staticmethod
    def validate_file_extension(filename: str) -> bool:
        """Validate file extension."""
        import os
        ext = os.path.splitext(filename.lower())[1]
        return ext in SecureImageUpload.ALLOWED_EXTENSIONS

    @staticmethod
    def validate_magic_bytes(data: bytes) -> bool:
        """
        Validate file magic bytes to ensure it's actually an image.
        This prevents content-type spoofing attacks.
        """
        # JPEG magic bytes
        if data[:3] == b'\xff\xd8\xff':
            return True
        # PNG magic bytes
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            return True
        # GIF magic bytes
        if data[:6] in (b'GIF87a', b'GIF89a'):
            return True
        # WebP magic bytes
        if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            return True
        return False


class SecureChatMessage(BaseModel):
    """Secure chat message validation."""
    message: str = Field(..., min_length=1, max_length=2000)
    context: Optional[str] = Field(None, max_length=5000)

    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = sanitize_string(v)
        check_dangerous_patterns(v, "message")
        return v

    @field_validator('context')
    @classmethod
    def validate_context(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return sanitize_string(v)


class SecureTierRequest(BaseModel):
    """Secure subscription tier request validation."""
    tier: str = Field(..., pattern=r'^(free|basic|pro|unlimited)$')

    @field_validator('tier')
    @classmethod
    def validate_tier(cls, v: str) -> str:
        return v.lower().strip()
