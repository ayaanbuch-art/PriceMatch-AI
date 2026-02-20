"""Authentication API endpoints with enterprise security."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import UserCreate, UserLogin, UserResponse, Token, AppleSignIn
from ..utils.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user
)
from ..utils.validators import SecureUserCreate, SecureUserLogin, SecureAppleSignIn
from ..utils.audit import audit_log, AuditAction, get_client_info
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=Token)
async def register(
    user_data: SecureUserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Register a new user with email/password."""
    client_info = get_client_info(request)

    # Check if user already exists (case-insensitive)
    existing_user = db.query(User).filter(
        User.email == user_data.email.lower()
    ).first()

    if existing_user:
        audit_log(
            AuditAction.REGISTER,
            email=user_data.email,
            success=False,
            error_message="Email already registered",
            **client_info
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user with hashed password
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email.lower(),
        password_hash=hashed_password,
        full_name=user_data.full_name,
        auth_provider="email"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Audit log for successful registration
    audit_log(
        AuditAction.REGISTER,
        user_id=new_user.id,
        email=new_user.email,
        success=True,
        **client_info
    )

    # Create access token
    access_token = create_access_token(data={"sub": str(new_user.id)})

    # Create user response with is_premium
    user_response = UserResponse(
        **new_user.__dict__,
        is_premium=new_user.is_premium()
    )

    return Token(access_token=access_token, user=user_response)


@router.post("/login", response_model=Token)
async def login(
    credentials: SecureUserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Login with email/password."""
    client_info = get_client_info(request)

    # Find user (case-insensitive email)
    user = db.query(User).filter(
        User.email == credentials.email.lower()
    ).first()

    # Use constant-time comparison to prevent timing attacks
    # Generic error message prevents user enumeration
    if not user or not user.password_hash:
        audit_log(
            AuditAction.LOGIN_FAILED,
            email=credentials.email,
            success=False,
            error_message="User not found or no password",
            **client_info
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        audit_log(
            AuditAction.LOGIN_FAILED,
            user_id=user.id,
            email=user.email,
            success=False,
            error_message="Invalid password",
            **client_info
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Successful login
    audit_log(
        AuditAction.LOGIN_SUCCESS,
        user_id=user.id,
        email=user.email,
        success=True,
        **client_info
    )

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})

    user_response = UserResponse(
        **user.__dict__,
        is_premium=user.is_premium()
    )

    return Token(access_token=access_token, user=user_response)


@router.post("/apple", response_model=Token)
async def apple_sign_in(
    apple_data: SecureAppleSignIn,
    request: Request,
    db: Session = Depends(get_db)
):
    """Sign in with Apple."""
    client_info = get_client_info(request)

    # Check if user exists by Apple user ID
    user = db.query(User).filter(
        User.auth_provider == "apple",
        User.auth_provider_id == apple_data.user_id
    ).first()

    if not user and apple_data.email:
        # Create new user
        user = User(
            email=apple_data.email.lower() if apple_data.email else None,
            full_name=apple_data.full_name,
            auth_provider="apple",
            auth_provider_id=apple_data.user_id
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        audit_log(
            AuditAction.APPLE_SIGNIN,
            user_id=user.id,
            email=user.email,
            success=True,
            details={"new_user": True},
            **client_info
        )

    elif not user:
        audit_log(
            AuditAction.APPLE_SIGNIN,
            success=False,
            error_message="User not found and no email provided",
            **client_info
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found and no email provided"
        )
    else:
        # Existing user login
        audit_log(
            AuditAction.APPLE_SIGNIN,
            user_id=user.id,
            email=user.email,
            success=True,
            details={"new_user": False},
            **client_info
        )

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})

    user_response = UserResponse(
        **user.__dict__,
        is_premium=user.is_premium()
    )

    return Token(access_token=access_token, user=user_response)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return UserResponse(
        **current_user.__dict__,
        is_premium=current_user.is_premium()
    )
