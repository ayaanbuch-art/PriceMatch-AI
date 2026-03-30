"""FastAPI application entry point with enterprise security."""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from .config import settings
from .database import engine, Base
from .api import auth, search, favorites, recommendations, subscription, analytics, chat, gamification, user, feedback, price_watch, community, wardrobe
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

# Run migrations for user preferences columns (safe to run multiple times)
from sqlalchemy import text
try:
    with engine.connect() as conn:
        # Add gender_preference column if it doesn't exist
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name = 'gender_preference'
                ) THEN
                    ALTER TABLE users ADD COLUMN gender_preference VARCHAR DEFAULT 'either';
                END IF;
            END $$;
        """))
        # Add style_preferences column if it doesn't exist
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name = 'style_preferences'
                ) THEN
                    ALTER TABLE users ADD COLUMN style_preferences JSON DEFAULT '[]';
                END IF;
            END $$;
        """))
        # Add preferred_sizes column if it doesn't exist
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name = 'preferred_sizes'
                ) THEN
                    ALTER TABLE users ADD COLUMN preferred_sizes JSON;
                END IF;
            END $$;
        """))
        conn.commit()
    logger.info("User preferences migration completed successfully")
except Exception as e:
    logger.warning(f"Migration check failed (may already exist): {e}")

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
app.include_router(user.router)
app.include_router(feedback.router)
app.include_router(price_watch.router)
app.include_router(community.router)
app.include_router(wardrobe.router)

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
        h3 { color: #ddd6fe; margin-top: 20px; }
        a { color: #818cf8; }
        .last-updated { color: #9ca3af; font-size: 14px; }
        .highlight-box { background: rgba(139, 92, 246, 0.1); border-left: 3px solid #8b5cf6; padding: 15px; margin: 15px 0; border-radius: 0 8px 8px 0; }
    </style>
</head>
<body>
    <h1>Privacy Policy</h1>
    <p class="last-updated">Last Updated: March 29, 2026</p>

    <p>PriceMatch AI ("we", "our", or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, and safeguard your information when you use our mobile application.</p>

    <h2>Information We Collect</h2>

    <h3>Account Information</h3>
    <p>When you create an account, we collect:</p>
    <ul>
        <li>Email address</li>
        <li>Name (optional)</li>
        <li>Authentication credentials (securely hashed)</li>
        <li>Style preferences and sizes (optional)</li>
    </ul>

    <h3>Photos and Images</h3>
    <p>Our app handles photos differently depending on the feature:</p>

    <div class="highlight-box">
        <strong>Visual Search Photos (Temporary):</strong>
        <p>When you use the visual search feature to find similar items, photos are processed in real-time and <strong>are NOT permanently stored</strong>. Images are temporarily uploaded for AI analysis and automatically deleted within 24 hours.</p>
    </div>

    <div class="highlight-box">
        <strong>Wardrobe Photos (Stored):</strong>
        <p>When you add items to your digital wardrobe, photos <strong>ARE stored on our servers</strong> to provide the wardrobe management and outfit suggestion features. These images remain stored until you delete them or delete your account.</p>
        <ul>
            <li>You can delete individual wardrobe items at any time</li>
            <li>You can delete all wardrobe photos by deleting your account</li>
            <li>Wardrobe photos are used to generate AI outfit suggestions</li>
            <li>Your wardrobe photos are private and never shared publicly</li>
        </ul>
    </div>

    <h3>Usage Data</h3>
    <p>We collect information about how you use the app, including:</p>
    <ul>
        <li>Search history and preferences</li>
        <li>Products viewed and favorited</li>
        <li>Wardrobe items and categories</li>
        <li>App feature usage patterns</li>
    </ul>

    <h2>How We Use Your Information</h2>
    <ul>
        <li><strong>Provide Services:</strong> To operate visual search, wardrobe management, and product recommendations</li>
        <li><strong>Personalization:</strong> To tailor product and outfit suggestions to your style</li>
        <li><strong>Wardrobe Features:</strong> To store and organize your clothing items and generate outfit ideas</li>
        <li><strong>Improve the App:</strong> To understand usage patterns and enhance our services</li>
        <li><strong>Communication:</strong> To send important updates about your account or our services</li>
    </ul>

    <h2>Third-Party AI Services</h2>
    <p><strong>Important:</strong> Our app uses third-party AI services. Here's exactly what data is shared:</p>

    <h3>Google Gemini AI (Image Analysis)</h3>
    <ul>
        <li><strong>What we send:</strong> Photos you take/upload for searching AND wardrobe items for AI analysis</li>
        <li><strong>Purpose:</strong> To analyze clothing items, identify brands, colors, styles, and generate outfit suggestions</li>
        <li><strong>Data retention:</strong> Google processes images in real-time; Google does not permanently store images from our API requests</li>
        <li><strong>Your consent:</strong> You will be asked to consent before any images are sent to Google Gemini AI</li>
    </ul>

    <h3>Google Shopping API (Product Search)</h3>
    <ul>
        <li><strong>What we send:</strong> Text descriptions of items (derived from AI analysis)</li>
        <li><strong>Purpose:</strong> To find matching products from online retailers</li>
        <li><strong>Data retention:</strong> Search queries are not stored by Google with your personal information</li>
    </ul>

    <h3>Other Third-Party Services</h3>
    <ul>
        <li><strong>Stripe:</strong> For secure payment processing (we do not store payment card details)</li>
        <li><strong>Apple Sign-In:</strong> For authentication (optional)</li>
        <li><strong>Cloudinary:</strong> For image hosting and storage</li>
    </ul>

    <p><strong>All third-party services we use provide equivalent data protection as described in this policy.</strong></p>

    <h2>User-Generated Content</h2>
    <p>When you upload photos to your wardrobe:</p>
    <ul>
        <li>You retain ownership of your photos</li>
        <li>You grant us a license to store, process, and display your photos within the app</li>
        <li>Your photos are used only to provide wardrobe and outfit suggestion services</li>
        <li>We do not sell, share publicly, or use your photos for advertising without consent</li>
        <li>You can delete your photos at any time through the app</li>
    </ul>

    <h2>Data Security</h2>
    <p>We implement industry-standard security measures including:</p>
    <ul>
        <li>Encryption of data in transit (HTTPS/TLS)</li>
        <li>Secure password hashing</li>
        <li>Secure cloud storage for wardrobe images</li>
        <li>Regular security audits</li>
        <li>Access controls and monitoring</li>
    </ul>

    <h2>Data Retention</h2>
    <ul>
        <li><strong>Account data:</strong> Retained while your account is active</li>
        <li><strong>Visual search images:</strong> Automatically deleted within 24 hours</li>
        <li><strong>Wardrobe images:</strong> Stored until you delete them or your account</li>
        <li><strong>Search history:</strong> Stored until you delete it or your account</li>
    </ul>
    <p>You can request deletion of your account and all associated data at any time through the app or by contacting us.</p>

    <h2>Your Rights</h2>
    <p>You have the right to:</p>
    <ul>
        <li>Access your personal data (via the Download My Data feature)</li>
        <li>Correct inaccurate data</li>
        <li>Delete individual wardrobe items</li>
        <li>Delete your entire account and all data</li>
        <li>Export your data</li>
        <li>Opt out of marketing communications</li>
        <li>Revoke AI consent at any time in Settings</li>
    </ul>

    <h2>Children's Privacy</h2>
    <p>Our app is not intended for children under 13. We do not knowingly collect personal information from children under 13. If you are a parent or guardian and believe your child has provided us with personal information, please contact us.</p>

    <h2>California Privacy Rights (CCPA)</h2>
    <p>If you are a California resident, you have additional rights under the CCPA, including the right to know what personal information we collect and the right to request deletion.</p>

    <h2>Changes to This Policy</h2>
    <p>We may update this Privacy Policy from time to time. We will notify you of any changes by posting the new Privacy Policy on this page and updating the "Last Updated" date. Material changes will be notified via email or in-app notification.</p>

    <h2>Contact Us</h2>
    <p>If you have any questions about this Privacy Policy, please contact us at:</p>
    <p>Email: <a href="mailto:fitcheckai2026@gmail.com">fitcheckai2026@gmail.com</a></p>

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
        h3 { color: #ddd6fe; margin-top: 20px; }
        a { color: #818cf8; }
        .last-updated { color: #9ca3af; font-size: 14px; }
        .highlight-box { background: rgba(139, 92, 246, 0.1); border-left: 3px solid #8b5cf6; padding: 15px; margin: 15px 0; border-radius: 0 8px 8px 0; }
    </style>
</head>
<body>
    <h1>Terms of Service</h1>
    <p class="last-updated">Last Updated: March 29, 2026</p>

    <p>Welcome to PriceMatch AI. By using our application, you agree to these Terms of Service.</p>

    <h2>1. Acceptance of Terms</h2>
    <p>By accessing or using PriceMatch AI, you agree to be bound by these Terms and our Privacy Policy. If you do not agree, please do not use our services.</p>

    <h2>2. Description of Service</h2>
    <p>PriceMatch AI is a fashion discovery app that provides:</p>
    <ul>
        <li><strong>Visual Search:</strong> Find similar or affordable alternatives to clothing items using AI image analysis</li>
        <li><strong>Digital Wardrobe:</strong> Upload and organize photos of your clothing to get AI-generated outfit suggestions</li>
        <li><strong>Product Recommendations:</strong> Personalized product suggestions based on your style preferences</li>
        <li><strong>Price Comparisons:</strong> Compare prices across multiple retailers</li>
    </ul>

    <h2>3. User Accounts</h2>
    <ul>
        <li>You must provide accurate information when creating an account</li>
        <li>You are responsible for maintaining the security of your account credentials</li>
        <li>You must be at least 13 years old to use this service</li>
        <li>You are responsible for all activity under your account</li>
        <li>You must notify us immediately of any unauthorized use of your account</li>
    </ul>

    <h2>4. User-Generated Content</h2>
    <p>When you upload photos to your wardrobe or use our visual search feature:</p>

    <h3>Content Ownership</h3>
    <p>You retain all ownership rights to the photos you upload. We do not claim ownership of your content.</p>

    <h3>License Grant</h3>
    <p>By uploading content to PriceMatch AI, you grant us a non-exclusive, worldwide, royalty-free license to:</p>
    <ul>
        <li>Store your photos on our servers</li>
        <li>Process your photos using AI services to provide wardrobe and outfit features</li>
        <li>Display your photos within the app (only visible to you)</li>
        <li>Create derivative data (such as clothing categories, colors, styles) from your photos</li>
    </ul>
    <p>This license exists only to enable us to provide our services. We will not publicly display, sell, or share your photos with third parties except as necessary to operate the service (e.g., sending to AI services for analysis).</p>

    <h3>Content Guidelines</h3>
    <p>You agree that content you upload will NOT contain:</p>
    <ul>
        <li>Nudity, sexually explicit, or pornographic material</li>
        <li>Violent, harmful, or disturbing content</li>
        <li>Content that infringes on others' intellectual property rights</li>
        <li>Content depicting illegal activities</li>
        <li>Personal information of others without their consent</li>
    </ul>
    <p>We reserve the right to remove any content that violates these guidelines.</p>

    <h3>Content Deletion</h3>
    <p>You can delete your uploaded content at any time through the app. When you delete wardrobe items, they are permanently removed from our servers. Account deletion will remove all your content.</p>

    <h2>5. Subscriptions and Payments</h2>
    <p>PriceMatch AI offers the following auto-renewable subscription options:</p>
    <ul>
        <li><strong>Basic:</strong> $4.99/month - 100 scans per month</li>
        <li><strong>Pro:</strong> $9.99/month - 500 scans per month</li>
        <li><strong>Unlimited:</strong> $19.99/month - Unlimited scans</li>
    </ul>

    <h3>Payment and Renewal Terms</h3>
    <ul>
        <li>Payment will be charged to your Apple ID account at confirmation of purchase</li>
        <li>Subscriptions automatically renew unless auto-renew is turned off at least 24 hours before the end of the current period</li>
        <li>Your account will be charged for renewal within 24 hours prior to the end of the current period</li>
        <li>You can manage and cancel your subscriptions by going to your App Store account settings after purchase</li>
        <li>Any unused portion of a free trial period, if offered, will be forfeited when you purchase a subscription</li>
    </ul>

    <h3>Managing Your Subscription</h3>
    <p>To cancel or manage your subscription:</p>
    <ol>
        <li>Open the Settings app on your device</li>
        <li>Tap your name at the top</li>
        <li>Tap "Subscriptions"</li>
        <li>Select PriceMatch AI</li>
        <li>Tap "Cancel Subscription" or modify your plan</li>
    </ol>
    <p>Or visit: <a href="https://apps.apple.com/account/subscriptions">https://apps.apple.com/account/subscriptions</a></p>

    <h3>Refunds</h3>
    <p>Refunds are handled according to Apple's refund policy. To request a refund, visit <a href="https://reportaproblem.apple.com">reportaproblem.apple.com</a>.</p>

    <h2>6. Third-Party Services</h2>
    <p>Our app uses third-party services to provide its features:</p>
    <ul>
        <li><strong>Google Gemini AI:</strong> For image analysis and outfit suggestions</li>
        <li><strong>Google Shopping API:</strong> For product search results</li>
        <li><strong>Cloudinary:</strong> For image storage</li>
        <li><strong>Stripe:</strong> For payment processing</li>
    </ul>
    <p>Your use of our service is also subject to the terms and privacy policies of these third-party providers. By using our service, you consent to the transfer of data to these services as described in our Privacy Policy.</p>

    <h2>7. Acceptable Use</h2>
    <p>You agree not to:</p>
    <ul>
        <li>Use the service for any illegal purpose</li>
        <li>Upload inappropriate, offensive, or prohibited content</li>
        <li>Attempt to reverse engineer, decompile, or hack the application</li>
        <li>Interfere with the proper functioning of the service</li>
        <li>Use automated systems or bots to access the service</li>
        <li>Attempt to bypass usage limits or subscription restrictions</li>
        <li>Impersonate others or misrepresent your identity</li>
        <li>Use the service to infringe on intellectual property rights</li>
    </ul>

    <h2>8. Intellectual Property</h2>
    <p>All content, features, and functionality of PriceMatch AI (excluding user-generated content) are owned by us and protected by copyright, trademark, and other intellectual property laws. You may not copy, modify, distribute, or create derivative works of our app without permission.</p>

    <h2>9. Disclaimer of Warranties</h2>
    <p>The service is provided "as is" and "as available" without warranties of any kind, either express or implied. We do not guarantee:</p>
    <ul>
        <li>The accuracy of AI analysis or outfit suggestions</li>
        <li>The accuracy of product recommendations or price information</li>
        <li>That products shown will be available or at the displayed price</li>
        <li>Uninterrupted or error-free service</li>
    </ul>

    <h2>10. Limitation of Liability</h2>
    <p>To the maximum extent permitted by law, we shall not be liable for any indirect, incidental, special, consequential, or punitive damages arising from your use of the service, including but not limited to:</p>
    <ul>
        <li>Loss of data or content</li>
        <li>Purchase decisions based on our recommendations</li>
        <li>Service interruptions or errors</li>
    </ul>

    <h2>11. Indemnification</h2>
    <p>You agree to indemnify and hold harmless PriceMatch AI from any claims, damages, or expenses arising from your use of the service, your content, or your violation of these Terms.</p>

    <h2>12. Termination</h2>
    <p>We may terminate or suspend your account at any time for violation of these Terms. Upon termination, your right to use the service will cease immediately. You may delete your account at any time through the app.</p>

    <h2>13. Changes to Terms</h2>
    <p>We reserve the right to modify these terms at any time. We will notify you of material changes via email or in-app notification. Continued use of the service after changes constitutes acceptance of updated terms.</p>

    <h2>14. Governing Law</h2>
    <p>These Terms shall be governed by and construed in accordance with the laws of the United States, without regard to conflict of law principles.</p>

    <h2>15. Contact</h2>
    <p>For questions about these Terms, contact us at: <a href="mailto:fitcheckai2026@gmail.com">fitcheckai2026@gmail.com</a></p>

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
