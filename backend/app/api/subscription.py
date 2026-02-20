"""Subscription API endpoints with secure payment handling."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
import stripe

from ..database import get_db
from ..models import User
from ..models.user import SUBSCRIPTION_TIERS
from ..schemas import SubscriptionStatus
from ..utils.auth import get_current_user
from ..utils.validators import SecureTierRequest
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/subscription", tags=["subscription"])

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Map tier IDs to Stripe Price IDs
TIER_TO_STRIPE_PRICE = {
    "basic": settings.STRIPE_PRICE_BASIC,
    "pro": settings.STRIPE_PRICE_PRO,
    "unlimited": settings.STRIPE_PRICE_UNLIMITED,
}

# Map Stripe Price IDs back to tier IDs
STRIPE_PRICE_TO_TIER = {v: k for k, v in TIER_TO_STRIPE_PRICE.items() if v}


class CheckoutRequest(BaseModel):
    """Request to create a Stripe checkout session."""
    tier: str  # 'basic', 'pro', 'unlimited'


@router.get("/status", response_model=SubscriptionStatus)
async def get_subscription_status(
    current_user: User = Depends(get_current_user)
):
    """Get current user's subscription status."""
    return SubscriptionStatus(
        is_premium=current_user.is_premium(),
        status=current_user.subscription_status,
        expires_at=current_user.subscription_expires_at,
        auto_renew_enabled=current_user.auto_renew_enabled or False,
        subscription_id=current_user.subscription_id
    )


@router.get("/usage")
async def get_usage_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get usage status based on subscription tier."""
    tier_info = current_user.get_tier_info()
    monthly_limit = current_user.get_monthly_scan_limit()
    remaining = current_user.get_remaining_scans()

    return {
        "tier": current_user.subscription_tier or "free",
        "tier_name": tier_info.get("name", "Free"),
        "monthly_limit": monthly_limit,
        "scans_used": current_user.monthly_scans_used or 0,
        "scans_remaining": remaining,
        "is_premium": current_user.is_premium(),
        "is_unlimited": monthly_limit == -1,
    }


@router.get("/tiers")
async def get_available_tiers():
    """Get all available subscription tiers."""
    tiers = []
    for tier_id, tier_info in SUBSCRIPTION_TIERS.items():
        tiers.append({
            "id": tier_id,
            "name": tier_info["name"],
            "monthly_scans": tier_info["monthly_scans"],
            "price": tier_info["price"],
            "is_premium": tier_info["is_premium"],
            "badge": tier_info.get("badge"),
        })
    return {"tiers": tiers}


# =============================================================================
# DEVELOPMENT-ONLY ENDPOINTS (Gated behind DEBUG flag)
# =============================================================================

@router.post("/select-tier")
async def select_subscription_tier(
    request: SecureTierRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Development endpoint to select a subscription tier.
    DISABLED IN PRODUCTION - Use Stripe checkout for real payments.
    """
    # SECURITY: Gate behind DEBUG flag
    if not settings.DEBUG:
        raise HTTPException(
            status_code=403,
            detail="This endpoint is disabled in production. Use /create-checkout-session for payments."
        )

    tier = request.tier.lower()

    if tier not in SUBSCRIPTION_TIERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier: {tier}. Valid tiers: {list(SUBSCRIPTION_TIERS.keys())}"
        )

    tier_info = SUBSCRIPTION_TIERS[tier]

    # Set subscription based on tier
    if tier == "free":
        current_user.subscription_status = "free"
        current_user.subscription_tier = "free"
        current_user.subscription_expires_at = None
        current_user.subscription_id = None
        current_user.auto_renew_enabled = False
    else:
        current_user.subscription_status = "active"
        current_user.subscription_tier = tier
        current_user.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        current_user.subscription_id = f"dev_{tier}_{current_user.id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        current_user.auto_renew_enabled = True

    db.commit()
    db.refresh(current_user)

    logger.info(f"Dev tier change: user_id={current_user.id}, tier={tier}")

    return {
        "success": True,
        "message": f"Successfully switched to {tier_info['name']} plan!",
        "tier": tier,
        "tier_name": tier_info["name"],
        "monthly_scans": tier_info["monthly_scans"],
        "price": tier_info["price"],
        "is_premium": current_user.is_premium(),
        "expires_at": current_user.subscription_expires_at.isoformat() if current_user.subscription_expires_at else None
    }


@router.post("/upgrade-dev")
async def upgrade_to_premium_dev(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Development endpoint to instantly upgrade user to unlimited tier.
    DISABLED IN PRODUCTION.
    """
    # SECURITY: Gate behind DEBUG flag
    if not settings.DEBUG:
        raise HTTPException(
            status_code=403,
            detail="This endpoint is disabled in production. Use /create-checkout-session for payments."
        )

    current_user.subscription_status = "active"
    current_user.subscription_tier = "unlimited"
    current_user.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    current_user.subscription_id = f"dev_unlimited_{current_user.id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    current_user.auto_renew_enabled = True

    db.commit()
    db.refresh(current_user)

    logger.info(f"Dev upgrade: user_id={current_user.id}")

    return {
        "success": True,
        "message": "Successfully upgraded to Unlimited!",
        "tier": "unlimited",
        "is_premium": current_user.is_premium(),
        "expires_at": current_user.subscription_expires_at.isoformat()
    }


@router.post("/downgrade-dev")
async def downgrade_from_premium_dev(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Development endpoint to downgrade user to free tier.
    DISABLED IN PRODUCTION.
    """
    # SECURITY: Gate behind DEBUG flag
    if not settings.DEBUG:
        raise HTTPException(
            status_code=403,
            detail="This endpoint is disabled in production."
        )

    current_user.subscription_status = "free"
    current_user.subscription_tier = "free"
    current_user.subscription_expires_at = None
    current_user.subscription_id = None
    current_user.auto_renew_enabled = False

    db.commit()
    db.refresh(current_user)

    logger.info(f"Dev downgrade: user_id={current_user.id}")

    return {
        "success": True,
        "message": "Downgraded to Free plan",
        "tier": "free",
        "is_premium": False
    }


# =============================================================================
# STRIPE PAYMENT ENDPOINTS (Production-ready)
# =============================================================================

@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Stripe Checkout session for subscription payment.
    Returns a checkout URL that the iOS app should open in Safari/WebView.
    """
    tier = request.tier.lower()

    # Validate tier
    if tier not in TIER_TO_STRIPE_PRICE:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier for payment: {tier}. Valid tiers: basic, pro, unlimited"
        )

    # Check if Stripe is configured
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="Payment system is not configured"
        )

    price_id = TIER_TO_STRIPE_PRICE[tier]
    if not price_id:
        raise HTTPException(
            status_code=500,
            detail=f"Price not configured for tier: {tier}"
        )

    try:
        # Get or create Stripe customer
        if current_user.stripe_customer_id:
            customer_id = current_user.stripe_customer_id
        else:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.full_name,
                metadata={
                    "user_id": str(current_user.id),
                }
            )
            current_user.stripe_customer_id = customer.id
            db.commit()
            customer_id = customer.id

        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=f"{settings.STRIPE_SUCCESS_URL}?session_id={{CHECKOUT_SESSION_ID}}&tier={tier}",
            cancel_url=settings.STRIPE_CANCEL_URL,
            metadata={
                "user_id": str(current_user.id),
                "tier": tier,
            },
            subscription_data={
                "metadata": {
                    "user_id": str(current_user.id),
                    "tier": tier,
                }
            },
            allow_promotion_codes=True,
        )

        logger.info(f"Checkout session created: user_id={current_user.id}, tier={tier}")

        return {
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id,
            "tier": tier,
        }

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error for user_id={current_user.id}: {type(e).__name__}")
        raise HTTPException(status_code=400, detail="Payment processing error")


@router.get("/billing-portal")
async def create_billing_portal_session(
    current_user: User = Depends(get_current_user),
):
    """
    Create a Stripe Customer Portal session for managing subscriptions.
    Returns a URL that the iOS app should open in Safari/WebView.
    """
    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No active subscription found. Please subscribe first."
        )

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=settings.STRIPE_SUCCESS_URL,
        )

        return {
            "portal_url": portal_session.url,
        }

    except stripe.error.StripeError as e:
        logger.error(f"Stripe portal error for user_id={current_user.id}: {type(e).__name__}")
        raise HTTPException(status_code=400, detail="Unable to access billing portal")


@router.post("/stripe-webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Stripe webhook events for subscription lifecycle.

    SECURITY: Webhook signature verification is MANDATORY.
    This prevents unauthorized webhook calls from modifying subscriptions.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # SECURITY: Always verify webhook signature
    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.error("Stripe webhook secret not configured - rejecting webhook")
        raise HTTPException(
            status_code=500,
            detail="Webhook configuration error"
        )

    if not sig_header:
        logger.warning("Stripe webhook received without signature")
        raise HTTPException(status_code=400, detail="Missing signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        logger.warning("Invalid Stripe webhook payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.warning("Invalid Stripe webhook signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.type
    data = event.data.object

    logger.info(f"Stripe webhook: {event_type}")

    # Handle different event types
    if event_type == "checkout.session.completed":
        await handle_checkout_completed(data, db)
    elif event_type == "invoice.paid":
        await handle_invoice_paid(data, db)
    elif event_type == "customer.subscription.updated":
        await handle_subscription_updated(data, db)
    elif event_type == "customer.subscription.deleted":
        await handle_subscription_deleted(data, db)
    elif event_type == "invoice.payment_failed":
        await handle_payment_failed(data, db)

    return {"status": "received"}


async def handle_checkout_completed(session, db: Session):
    """Handle successful checkout - activate subscription."""
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    metadata = session.get("metadata", {})
    tier = metadata.get("tier")
    user_id = metadata.get("user_id")

    if not user_id:
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    else:
        user = db.query(User).filter(User.id == int(user_id)).first()

    if user and tier:
        user.subscription_status = "active"
        user.subscription_tier = tier
        user.subscription_id = subscription_id
        user.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        user.auto_renew_enabled = True
        db.commit()
        logger.info(f"Subscription activated: user_id={user.id}, tier={tier}")


async def handle_invoice_paid(invoice, db: Session):
    """Handle successful recurring payment - extend subscription."""
    customer_id = invoice.get("customer")

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

    if user:
        user.subscription_status = "active"
        user.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        db.commit()
        logger.info(f"Subscription renewed: user_id={user.id}")


async def handle_subscription_updated(subscription, db: Session):
    """Handle subscription updates (plan changes, etc.)."""
    customer_id = subscription.get("customer")
    status = subscription.get("status")
    items = subscription.get("items", {}).get("data", [])

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

    if user and items:
        price_id = items[0].get("price", {}).get("id")
        new_tier = STRIPE_PRICE_TO_TIER.get(price_id)

        if new_tier:
            user.subscription_tier = new_tier
            user.subscription_status = "active" if status == "active" else status
            db.commit()
            logger.info(f"Subscription updated: user_id={user.id}, tier={new_tier}")


async def handle_subscription_deleted(subscription, db: Session):
    """Handle subscription cancellation."""
    customer_id = subscription.get("customer")

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

    if user:
        user.subscription_status = "cancelled"
        user.subscription_tier = "free"
        user.auto_renew_enabled = False
        db.commit()
        logger.info(f"Subscription cancelled: user_id={user.id}")


async def handle_payment_failed(invoice, db: Session):
    """Handle failed payment."""
    customer_id = invoice.get("customer")

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

    if user:
        logger.warning(f"Payment failed: user_id={user.id}")
        # Note: Don't immediately cancel - Stripe has retry logic
        # Just log for now, subscription status will be updated by subscription.updated event


# =============================================================================
# APPLE APP STORE WEBHOOK (Legacy - Not Implemented)
# =============================================================================

@router.post("/webhook")
async def apple_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Apple App Store Server-to-Server notifications.
    NOTE: Apple App Store integration requires additional verification.
    This endpoint is a placeholder for future implementation.
    """
    # For security, return received but don't process unverified webhooks
    logger.warning("Apple webhook received but verification not implemented")

    return {"status": "received"}
