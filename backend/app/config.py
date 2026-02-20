"""Application configuration."""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""

    # Database
    DATABASE_URL: str

    # JWT Authentication
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    # SECURITY: Token expires in 60 minutes (industry best practice)
    # For better UX, implement refresh tokens for longer sessions
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    # Refresh token expiration (7 days) - for future implementation
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Google Gemini API
    GOOGLE_GEMINI_API_KEY: str

    # AWS S3 (Optional/Deprecated for Local MVP)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = ""
    AWS_REGION: str = "us-east-1"

    # Google Shopping API
    GOOGLE_SHOPPING_API_KEY: str = ""

    # Affiliate Networks
    AMAZON_ASSOCIATE_TAG: str = ""
    AMAZON_ACCESS_KEY: str = ""
    AMAZON_SECRET_KEY: str = ""

    # App Configuration
    ENVIRONMENT: str = "development"
    # SECURITY: DEBUG defaults to False - must be explicitly enabled
    DEBUG: bool = False
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Stripe Payment Processing
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_SUCCESS_URL: str = "pricematchai://payment-success"
    STRIPE_CANCEL_URL: str = "pricematchai://payment-cancel"

    # Stripe Price IDs (create these in Stripe Dashboard)
    STRIPE_PRICE_BASIC: str = ""  # $4.99/month
    STRIPE_PRICE_PRO: str = ""    # $9.99/month
    STRIPE_PRICE_UNLIMITED: str = ""  # $19.99/month

    # Apple App Store (Optional for MVP)
    APPLE_BUNDLE_ID: str = ""
    APPLE_SHARED_SECRET: str = ""

    # Search APIs
    SERPAPI_API_KEY: str = ""

    # Base URL for image paths
    BASE_URL: str = "http://127.0.0.1:8000"

    # Usage Limits
    FREE_TIER_DAILY_SEARCHES: int = 5

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
