"""Audit logging for security-sensitive operations."""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger("snapstyle.audit")


class AuditAction(str, Enum):
    """Audit action types."""
    # Authentication
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    REGISTER = "register"
    PASSWORD_CHANGE = "password_change"
    APPLE_SIGNIN = "apple_signin"

    # Subscription
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    SUBSCRIPTION_UPGRADED = "subscription_upgraded"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"

    # Data Access
    SEARCH_PERFORMED = "search_performed"
    HISTORY_ACCESSED = "history_accessed"
    HISTORY_DELETED = "history_deleted"
    FAVORITES_MODIFIED = "favorites_modified"

    # Account
    ACCOUNT_DELETED = "account_deleted"
    PROFILE_UPDATED = "profile_updated"

    # Security Events
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INVALID_TOKEN = "invalid_token"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


def audit_log(
    action: AuditAction,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> None:
    """
    Log an audit event for security-sensitive operations.

    Args:
        action: The type of action being audited
        user_id: The user performing the action (if authenticated)
        email: The email involved (for auth events)
        ip_address: Client IP address
        user_agent: Client user agent
        success: Whether the action succeeded
        details: Additional context about the action
        error_message: Error message if action failed
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action.value,
        "user_id": user_id,
        "email": _mask_email(email) if email else None,
        "ip_address": ip_address,
        "user_agent": user_agent[:200] if user_agent else None,  # Truncate long UAs
        "success": success,
        "details": details,
        "error": error_message
    }

    # Remove None values for cleaner logs
    log_entry = {k: v for k, v in log_entry.items() if v is not None}

    # Log with appropriate level
    if success:
        logger.info(f"AUDIT: {log_entry}")
    else:
        logger.warning(f"AUDIT: {log_entry}")


def _mask_email(email: str) -> str:
    """Mask email for logging (show first 2 chars and domain)."""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[:2] + "*" * (len(local) - 2)
    return f"{masked_local}@{domain}"


def get_client_info(request) -> Dict[str, str]:
    """Extract client information from request for audit logging."""
    # Get IP address (handle proxies)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"

    return {
        "ip_address": ip,
        "user_agent": request.headers.get("User-Agent", "unknown")
    }
