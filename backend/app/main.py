"""FastAPI application entry point with enterprise security."""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import engine, Base
from .api import auth, search, favorites, recommendations, subscription, analytics, chat, gamification
from .middleware.security import setup_security_middleware

# Configure logging - secure by default
logging.basicConfig(
    level=logging.WARNING if not settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log') if not settings.DEBUG else logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app with production settings
app = FastAPI(
    title="PriceMatch AI API",
    description="Backend API for PriceMatch AI fashion discovery app",
    version="1.0.0",
    # Disable docs in production for security
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

# Configure CORS with strict settings
# In production, specify exact origins - never use wildcards
ALLOWED_ORIGINS = settings.CORS_ORIGINS if settings.DEBUG else [
    "https://snapstyle.ai",
    "https://www.snapstyle.ai",
    "https://api.snapstyle.ai",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    # Restrict methods to only what's needed
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    # Restrict headers
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
    # Expose rate limit headers
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Apply security middleware (CSP, HSTS, X-Frame-Options, etc.)
setup_security_middleware(app)

# Include routers
app.include_router(auth.router)
app.include_router(search.router)
app.include_router(favorites.router)
app.include_router(recommendations.router)
app.include_router(subscription.router)
app.include_router(analytics.router)
app.include_router(chat.router)
app.include_router(gamification.router)

# Mount static files with security considerations
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    """Root endpoint - minimal information disclosure."""
    return {
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    # Production: use proper ASGI server (gunicorn + uvicorn workers)
    # Development: direct uvicorn with reload
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        # Security settings
        server_header=False,
        date_header=False,
    )
