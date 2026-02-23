"""Authentication utilities with secure token handling."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import User
from ..schemas import TokenData

logger = logging.getLogger(__name__)

# Password hashing with bcrypt
# Use 12 rounds for good security/performance balance
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__default_rounds=12
)

# HTTP Bearer token authentication
security = HTTPBearer()


def _truncate_password(password: str) -> bytes:
    """Truncate password to 72 bytes (bcrypt limit)."""
    return password.encode('utf-8')[:72]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash using constant-time comparison."""
    try:
        truncated = _truncate_password(plain_password)
        return pwd_context.verify(truncated, hashed_password)
    except Exception:
        # Log internally but don't expose error details
        logger.warning("Password verification error")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt (truncated to 72 bytes)."""
    truncated = _truncate_password(password)
    return pwd_context.hash(truncated)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Claims to encode in the token
        expires_delta: Custom expiration time

    Returns:
        Encoded JWT string
    """
    to_encode = data.copy()

    # Set expiration
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),  # Issued at
        "type": "access"  # Token type for future refresh token support
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT string to decode

    Returns:
        TokenData with user_id

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={
                "verify_exp": True,
                "verify_iat": True,
                "require": ["sub", "exp"]
            }
        )

        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )

        user_id = int(user_id_str)
        return TokenData(user_id=user_id)

    except JWTError:
        # Generic error - don't leak whether token was expired, invalid, etc.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except ValueError:
        # Invalid user_id format
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from the JWT token.

    Args:
        credentials: Bearer token from Authorization header
        db: Database session

    Returns:
        The authenticated User object

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    token_data = decode_token(token)

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


async def get_current_premium_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and verify premium subscription.

    Args:
        current_user: The authenticated user

    Returns:
        The authenticated premium User

    Raises:
        HTTPException: If user doesn't have premium subscription
    """
    if not current_user.is_premium():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required"
        )
    return current_user
