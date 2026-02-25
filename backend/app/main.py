"""FastAPI application entry point with enterprise security."""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

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


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    """Privacy Policy page for App Store compliance."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Privacy Policy - PriceMatch AI</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
        }
        h1 { color: #a78bfa; border-bottom: 2px solid #8b5cf6; padding-bottom: 10px; }
        h2 { color: #c4b5fd; margin-top: 30px; }
        a { color: #818cf8; }
        .last-updated { color: #9ca3af; font-size: 14px; }
    </style>
</head>
<body>
    <h1>Privacy Policy</h1>
    <p class="last-updated">Last Updated: February 24, 2026</p>

    <p>PriceMatch AI ("we", "our", or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, and safeguard your information when you use our mobile application.</p>

    <h2>Information We Collect</h2>
    <h3>Account Information</h3>
    <p>When you create an account, we collect:</p>
    <ul>
        <li>Email address</li>
        <li>Name (optional)</li>
        <li>Authentication credentials (securely hashed)</li>
    </ul>

    <h3>Photos</h3>
    <p>When you use our visual search feature, we process photos you take or upload to:</p>
    <ul>
        <li>Analyze clothing and fashion items</li>
        <li>Find similar products and alternatives</li>
        <li>Provide personalized recommendations</li>
    </ul>
    <p><strong>We do not permanently store your photos.</strong> Images are processed in real-time and are not retained after analysis is complete.</p>

    <h3>Usage Data</h3>
    <p>We collect information about how you use the app, including:</p>
    <ul>
        <li>Search history and preferences</li>
        <li>Products viewed and favorited</li>
        <li>App feature usage patterns</li>
    </ul>

    <h2>How We Use Your Information</h2>
    <ul>
        <li><strong>Provide Services:</strong> To operate the visual search and product recommendation features</li>
        <li><strong>Personalization:</strong> To tailor product suggestions to your style preferences</li>
        <li><strong>Improve the App:</strong> To understand usage patterns and enhance our services</li>
        <li><strong>Communication:</strong> To send important updates about your account or our services</li>
    </ul>

    <h2>Third-Party Services</h2>
    <p>We use the following third-party services:</p>
    <ul>
        <li><strong>Google Gemini AI:</strong> For image analysis and fashion recommendations</li>
        <li><strong>Stripe:</strong> For secure payment processing (we do not store payment card details)</li>
        <li><strong>Apple Sign-In:</strong> For authentication (optional)</li>
    </ul>

    <h2>Data Security</h2>
    <p>We implement industry-standard security measures including:</p>
    <ul>
        <li>Encryption of data in transit (HTTPS/TLS)</li>
        <li>Secure password hashing</li>
        <li>Regular security audits</li>
        <li>Access controls and monitoring</li>
    </ul>

    <h2>Data Retention</h2>
    <p>We retain your account data for as long as your account is active. You can request deletion of your account and associated data at any time by contacting us.</p>

    <h2>Your Rights</h2>
    <p>You have the right to:</p>
    <ul>
        <li>Access your personal data</li>
        <li>Correct inaccurate data</li>
        <li>Delete your account and data</li>
        <li>Export your data</li>
        <li>Opt out of marketing communications</li>
    </ul>

    <h2>Children's Privacy</h2>
    <p>Our app is not intended for children under 13. We do not knowingly collect personal information from children under 13.</p>

    <h2>Changes to This Policy</h2>
    <p>We may update this Privacy Policy from time to time. We will notify you of any changes by posting the new Privacy Policy on this page and updating the "Last Updated" date.</p>

    <h2>Contact Us</h2>
    <p>If you have any questions about this Privacy Policy, please contact us at:</p>
    <p>Email: <a href="mailto:support@pricematchai.com">support@pricematchai.com</a></p>

    <p style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #374151; color: #9ca3af; font-size: 14px;">
        © 2026 PriceMatch AI. All rights reserved.
    </p>
</body>
</html>
"""


@app.get("/terms", response_class=HTMLResponse)
async def terms_of_service():
    """Terms of Service page for App Store compliance."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terms of Service - PriceMatch AI</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
        }
        h1 { color: #a78bfa; border-bottom: 2px solid #8b5cf6; padding-bottom: 10px; }
        h2 { color: #c4b5fd; margin-top: 30px; }
        a { color: #818cf8; }
        .last-updated { color: #9ca3af; font-size: 14px; }
    </style>
</head>
<body>
    <h1>Terms of Service</h1>
    <p class="last-updated">Last Updated: February 24, 2026</p>

    <p>Welcome to PriceMatch AI. By using our application, you agree to these Terms of Service.</p>

    <h2>1. Acceptance of Terms</h2>
    <p>By accessing or using PriceMatch AI, you agree to be bound by these Terms. If you do not agree, please do not use our services.</p>

    <h2>2. Description of Service</h2>
    <p>PriceMatch AI is a fashion discovery app that helps users find affordable alternatives to clothing items using AI-powered image analysis. Features include visual search, product recommendations, and price comparisons.</p>

    <h2>3. User Accounts</h2>
    <ul>
        <li>You must provide accurate information when creating an account</li>
        <li>You are responsible for maintaining the security of your account</li>
        <li>You must be at least 13 years old to use this service</li>
    </ul>

    <h2>4. Subscriptions and Payments</h2>
    <ul>
        <li>Some features require a paid subscription</li>
        <li>Subscriptions automatically renew unless cancelled</li>
        <li>Payments are processed securely through Apple's App Store</li>
        <li>Refunds are handled according to Apple's refund policy</li>
    </ul>

    <h2>5. Acceptable Use</h2>
    <p>You agree not to:</p>
    <ul>
        <li>Use the service for any illegal purpose</li>
        <li>Upload inappropriate or offensive content</li>
        <li>Attempt to reverse engineer the application</li>
        <li>Interfere with the proper functioning of the service</li>
    </ul>

    <h2>6. Intellectual Property</h2>
    <p>All content, features, and functionality of PriceMatch AI are owned by us and protected by copyright and other intellectual property laws.</p>

    <h2>7. Disclaimer of Warranties</h2>
    <p>The service is provided "as is" without warranties of any kind. We do not guarantee the accuracy of product recommendations or price information.</p>

    <h2>8. Limitation of Liability</h2>
    <p>We shall not be liable for any indirect, incidental, or consequential damages arising from your use of the service.</p>

    <h2>9. Changes to Terms</h2>
    <p>We reserve the right to modify these terms at any time. Continued use of the service constitutes acceptance of updated terms.</p>

    <h2>10. Contact</h2>
    <p>For questions about these Terms, contact us at: <a href="mailto:support@pricematchai.com">support@pricematchai.com</a></p>

    <p style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #374151; color: #9ca3af; font-size: 14px;">
        © 2026 PriceMatch AI. All rights reserved.
    </p>
</body>
</html>
"""


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
