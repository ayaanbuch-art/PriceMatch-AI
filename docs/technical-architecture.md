# PriceMatch AI - Technical Architecture (MVP Focus)

> **Note:** This document covers the **MVP architecture** focused on visual search with detailed descriptions.
> Post-MVP features (AI chatbot, wardrobe analyzer) are marked as such throughout the document.

## System Overview

PriceMatch AI is a client-server application with three main components:
1. **iOS Mobile App** - SwiftUI-based native iOS application
2. **Backend API** - RESTful API server handling business logic and AI integration
3. **External Services** - Google Gemini Vision, Apple IAP, Affiliate Networks, Cloud Storage

### MVP Scope
- Visual search with thorough AI-powered descriptions
- User authentication and accounts
- Product results with affiliate links
- Personalized recommendations
- Subscription monetization (Apple IAP)

### MVP Architecture Diagram
```
┌────────────────────────────────────────────────────────────────┐
│                      iOS App (SwiftUI MVP)                     │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────┐             │
│  │  Camera  │  │Search Results│  │Recommendations│  [Profile]  │
│  │  Search  │  │   (Depop)    │  │  ("For You") │             │
│  └──────────┘  └──────────────┘  └─────────────┘             │
└───────────────────────────┬────────────────────────────────────┘
                            │ HTTPS/REST
                            ▼
┌────────────────────────────────────────────────────────────────┐
│                  Backend API (FastAPI MVP)                     │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  ┌──────────┐ │
│  │   Auth   │  │  Visual  │  │Recommendations│  │Subscription│ │
│  │          │  │  Search  │  │   & Favorites │  │  (Apple)   │ │
│  └──────────┘  └──────────┘  └───────────────┘  └──────────┘ │
└───────┬─────────────┬──────────────┬──────────────┬───────────┘
        │             │              │              │
        ▼             ▼              ▼              ▼
┌──────────────┐ ┌─────────────┐ ┌──────────┐ ┌──────────────┐
│  PostgreSQL  │ │Google Gemini│ │ Apple    │ │ Affiliate    │
│   Database   │ │   Vision    │ │ StoreKit │ │   Networks   │
└──────────────┘ └─────────────┘ └──────────┘ └──────────────┘

Post-MVP additions: Chat module, Wardrobe module
```

---

## Backend Architecture

### Recommended Tech Stack
- **Framework:** FastAPI (Python 3.11+)
- **Database:** PostgreSQL 15+
- **Cache:** Redis (optional, for sessions and API caching)
- **Storage:** AWS S3 or Google Cloud Storage
- **Hosting:** AWS EC2, Google Cloud Run, or Railway

### Project Structure (MVP)
```
backend/
├── app/
│   ├── main.py                 # FastAPI app initialization
│   ├── config.py               # Environment variables and settings
│   ├── database.py             # Database connection and session
│   ├── models/                 # SQLAlchemy ORM models (MVP)
│   │   ├── user.py
│   │   ├── search_history.py
│   │   ├── favorite.py
│   │   ├── user_interaction.py
│   │   └── subscription.py
│   ├── schemas/                # Pydantic schemas for request/response
│   │   ├── user.py
│   │   ├── search.py
│   │   ├── product.py
│   │   └── subscription.py
│   ├── api/                    # API route handlers (MVP)
│   │   ├── auth.py
│   │   ├── search.py
│   │   ├── favorites.py
│   │   ├── recommendations.py
│   │   └── subscription.py
│   ├── services/               # Business logic (MVP)
│   │   ├── gemini.py           # Google Gemini Vision integration
│   │   ├── product_search.py  # Product matching logic
│   │   ├── affiliate.py        # Affiliate link generation
│   │   ├── recommendations.py  # Recommendation algorithm
│   │   └── payment.py          # Apple IAP integration
│   ├── utils/                  # Helper functions
│   │   ├── auth.py             # JWT token handling
│   │   ├── image.py            # Image preprocessing
│   │   └── similarity.py       # Similarity scoring
│   └── prompts/                # AI prompt templates (MVP)
│       └── visual_search.py    # Detailed analysis prompts
├── migrations/                 # Alembic database migrations
├── tests/                      # Unit and integration tests
├── requirements.txt
└── .env.example

Post-MVP additions:
- models/chat_message.py, wardrobe.py
- schemas/chat.py, wardrobe.py
- api/chat.py, wardrobe.py
- prompts/chatbot.py, wardrobe.py
```

---

## API Endpoints (MVP)

### Authentication (MVP)
```
POST   /api/auth/register          # Create new user account
POST   /api/auth/login             # Login with email/password
POST   /api/auth/apple             # Apple Sign-In (required for iOS)
POST   /api/auth/refresh           # Refresh JWT token
GET    /api/users/me               # Get current user profile
PUT    /api/users/me               # Update user profile
```

### Visual Search (MVP)
```
POST   /api/search/image           # Upload image, get AI analysis + products
GET    /api/search/history         # Get user's search history
GET    /api/search/:id             # Get specific search results
```

### Favorites (MVP)
```
POST   /api/favorites              # Save product to favorites
DELETE /api/favorites/:productId  # Remove from favorites
GET    /api/favorites              # Get all favorited items
```

### Recommendations (MVP)
```
GET    /api/recommendations        # Get personalized product feed
POST   /api/recommendations/track  # Track user interactions
```

### Subscription (MVP - Apple IAP)
```
GET    /api/subscription/status    # Get current subscription status
POST   /api/subscription/webhook   # Apple App Store webhook handler
GET    /api/subscription/usage     # Get usage limits (searches today)
```

### Products (MVP)
```
POST   /api/products/:id/click     # Track affiliate link click
```

---

## Post-MVP API Endpoints

### Chat (Post-MVP)
```
POST   /api/chat/message           # Send message to AI chatbot
GET    /api/chat/history           # Get chat conversation history
GET    /api/chat/conversations     # Get list of conversations
DELETE /api/chat/:conversationId   # Delete conversation
```

### Wardrobe (Post-MVP)
```
POST   /api/wardrobe               # Upload wardrobe photo
GET    /api/wardrobe               # Get user's wardrobe items
GET    /api/wardrobe/:id           # Get specific wardrobe item
DELETE /api/wardrobe/:id           # Delete wardrobe item
POST   /api/wardrobe/outfits       # Generate outfit suggestions
GET    /api/wardrobe/outfits       # Get saved outfits
POST   /api/wardrobe/outfits/:id/favorite  # Save outfit
```

---

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),  -- nullable for OAuth users
    full_name VARCHAR(255),
    profile_image_url TEXT,
    auth_provider VARCHAR(50) DEFAULT 'email',  -- 'email', 'apple', 'google'
    auth_provider_id VARCHAR(255),
    subscription_status VARCHAR(50) DEFAULT 'free',  -- 'free', 'active', 'cancelled'
    subscription_id VARCHAR(255),  -- Stripe subscription ID
    subscription_end_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Search History Table
```sql
CREATE TABLE search_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    search_query TEXT,  -- Generated by Gemini from image
    search_type VARCHAR(50),  -- 'clothing', 'shoes', 'accessories'
    results_data JSONB,  -- Store product results
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_search_user ON search_history(user_id);
CREATE INDEX idx_search_created ON search_history(created_at DESC);
```

### Favorites Table
```sql
CREATE TABLE favorites (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    product_id VARCHAR(255) NOT NULL,
    product_data JSONB NOT NULL,  -- Store product details
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, product_id)
);

CREATE INDEX idx_favorites_user ON favorites(user_id);
```

### Chat Messages Table
```sql
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL,
    role VARCHAR(50) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_chat_user_conversation ON chat_messages(user_id, conversation_id);
CREATE INDEX idx_chat_created ON chat_messages(created_at DESC);
```

### Wardrobe Table
```sql
CREATE TABLE wardrobe_items (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    items JSONB NOT NULL,  -- Array of detected clothing items
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_wardrobe_user ON wardrobe_items(user_id);
```

### Wardrobe Outfits Table
```sql
CREATE TABLE wardrobe_outfits (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255),
    style_filter VARCHAR(100),  -- 'date_night', 'casual', 'streetwear', etc.
    items JSONB NOT NULL,  -- Array of wardrobe item IDs in outfit
    is_favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_outfits_user ON wardrobe_outfits(user_id);
```

### User Interactions Table (for recommendations)
```sql
CREATE TABLE user_interactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    product_id VARCHAR(255) NOT NULL,
    interaction_type VARCHAR(50) NOT NULL,  -- 'view', 'click', 'favorite', 'purchase'
    product_category VARCHAR(100),
    product_price DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_interactions_user ON user_interactions(user_id);
CREATE INDEX idx_interactions_created ON user_interactions(created_at DESC);
```

---

## iOS App Architecture

### Tech Stack
- **Language:** Swift 5.9+
- **UI:** SwiftUI
- **Min iOS:** 16.0
- **Architecture:** MVVM (Model-View-ViewModel)
- **Networking:** URLSession with async/await
- **Image Loading:** AsyncImage or Kingfisher
- **Payment:** Stripe SDK or StoreKit 2
- **Camera:** AVFoundation

### Project Structure
```
SnapStyleAI/
├── SnapStyleAIApp.swift        # App entry point
├── Models/                     # Data models
│   ├── User.swift
│   ├── Product.swift
│   ├── ChatMessage.swift
│   ├── WardrobeItem.swift
│   └── SearchResult.swift
├── ViewModels/                 # Business logic
│   ├── AuthViewModel.swift
│   ├── SearchViewModel.swift
│   ├── ChatViewModel.swift
│   ├── WardrobeViewModel.swift
│   └── SubscriptionViewModel.swift
├── Views/                      # SwiftUI views
│   ├── Auth/
│   │   ├── LoginView.swift
│   │   ├── SignUpView.swift
│   │   └── OnboardingView.swift
│   ├── Search/
│   │   ├── CameraView.swift
│   │   ├── SearchResultsView.swift
│   │   └── ProductCardView.swift
│   ├── Chat/
│   │   ├── ChatView.swift
│   │   └── MessageBubbleView.swift
│   ├── Wardrobe/
│   │   ├── WardrobeView.swift
│   │   ├── OutfitGeneratorView.swift
│   │   └── OutfitCardView.swift
│   ├── Profile/
│   │   ├── ProfileView.swift
│   │   ├── SubscriptionView.swift
│   │   └── SettingsView.swift
│   └── Components/
│       ├── LoadingView.swift
│       └── ErrorView.swift
├── Services/                   # API and business services
│   ├── APIService.swift        # Network layer
│   ├── AuthService.swift
│   ├── ImageService.swift
│   └── SubscriptionService.swift
├── Utils/                      # Helper utilities
│   ├── KeychainHelper.swift    # Secure token storage
│   ├── ImageProcessor.swift
│   └── Constants.swift
└── Resources/                  # Assets and configs
    ├── Assets.xcassets
    └── Info.plist
```

### Key SwiftUI Views

#### Main Tab Navigation
```swift
TabView {
    SearchView()
        .tabItem { Label("Search", systemImage: "camera.fill") }

    RecommendationsView()
        .tabItem { Label("For You", systemImage: "heart.fill") }

    ChatView()
        .tabItem { Label("Chat", systemImage: "message.fill") }

    WardrobeView()
        .tabItem { Label("Wardrobe", systemImage: "tshirt.fill") }

    ProfileView()
        .tabItem { Label("Profile", systemImage: "person.fill") }
}
```

#### Camera Capture Flow
1. User taps camera button
2. Present camera view with AVCaptureSession
3. User captures photo or selects from library
4. Show preview with confirm/retake options
5. Upload to backend with loading indicator
6. Navigate to results view

#### Product Results Grid (Depop-style)
```swift
LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())]) {
    ForEach(products) { product in
        ProductCardView(product: product)
            .onTapGesture {
                // Open product detail
            }
    }
}
```

Each ProductCard shows:
- Async-loaded product image
- Brand and item name
- Price
- Similarity percentage badge
- Heart icon for favoriting

---

## Google Gemini Integration

### Visual Search Prompt Template
```python
def create_visual_search_prompt(image_data):
    return f"""
    Analyze this clothing/shoe image and provide detailed information:

    1. Item type (e.g., "dress", "sneakers", "jacket")
    2. Style category (e.g., "casual", "formal", "streetwear")
    3. Color(s)
    4. Material/fabric (if identifiable)
    5. Key features (patterns, embellishments, unique details)
    6. Estimated brand or style (if recognizable)
    7. Suggested search terms for finding similar items

    Format your response as JSON:
    {{
        "item_type": "",
        "style": "",
        "colors": [],
        "material": "",
        "features": [],
        "brand_style": "",
        "search_terms": []
    }}
    """
```

### Chatbot System Prompt
```python
FASHION_CHATBOT_PROMPT = """
You are a knowledgeable and friendly fashion AI assistant integrated into PriceMatch AI app.

Your capabilities:
- Answer questions about fashion trends, styles, and clothing
- Recommend TikTok and Instagram influencers for fashion inspiration
- Suggest outfit combinations and styling tips
- Help users describe items they want to find
- Provide shopping advice (quality, value, versatility)

Your personality:
- Enthusiastic about fashion but not pushy
- Helpful and conversational
- Up-to-date on current trends
- Inclusive and body-positive
- Budget-conscious and value-focused

When users describe an item they want, generate search terms and offer to search for it.
When users ask about influencers, provide 3-5 relevant suggestions with brief descriptions.
"""
```

### Wardrobe Outfit Prompt
```python
def create_outfit_prompt(wardrobe_items, style_filter):
    return f"""
    Given these clothing items from a user's wardrobe:
    {json.dumps(wardrobe_items)}

    Create 5 complete outfit combinations for the style: "{style_filter}"

    Requirements:
    - Each outfit must use only items from the provided wardrobe
    - Outfits should be practical and cohesive
    - Consider color coordination and style matching
    - Each outfit should be different and versatile

    Format response as JSON array:
    [
        {{
            "name": "Outfit name",
            "items": ["item_id_1", "item_id_2", ...],
            "description": "Brief styling notes",
            "occasion": "When to wear this"
        }}
    ]
    """
```

---

## External Service Integration

### Google Gemini API
- **Model:** gemini-1.5-pro or gemini-1.5-flash
- **Rate Limits:** Monitor usage, implement caching
- **Cost Optimization:**
  - Compress images before upload
  - Cache common queries
  - Use flash model for simple queries

### Stripe Integration
- **Webhook Events to Handle:**
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.payment_succeeded`
  - `invoice.payment_failed`

### Affiliate Networks
**Priority Networks:**
1. **Amazon Associates** - Broad product coverage
2. **ShareASale** - Fashion retailers
3. **CJ Affiliate (Commission Junction)** - Premium brands
4. **Rakuten Advertising** - Department stores

**Implementation:**
- Store affiliate tracking IDs in database
- Generate deep links with attribution
- Track clicks before redirect
- Report conversions via postback URLs

---

## Security Considerations

### API Authentication
- JWT tokens with 7-day expiration
- Refresh token rotation
- Secure token storage in iOS Keychain
- HTTPS only in production

### Data Privacy
- Encrypt user images at rest
- Hash and salt passwords with bcrypt
- Delete old search history after 90 days (configurable)
- GDPR-compliant data export and deletion

### Rate Limiting
- Per-user limits on API endpoints
- Free tier: 10 searches/day
- Premium: Unlimited (with reasonable abuse prevention)
- Chatbot: 100 messages/day for free, unlimited for premium

### Input Validation
- Sanitize all user inputs
- Validate image file types and sizes
- Prevent SQL injection with parameterized queries
- XSS protection in chat messages

---

## Performance Optimization

### Image Handling
- Max upload size: 10MB
- Compress to JPEG with 80% quality before upload
- Generate thumbnails on backend
- Use CDN for product images
- Lazy loading in iOS app

### API Caching
- Cache product search results for 1 hour
- Cache chat responses for identical queries
- Redis for session storage
- CDN caching for static assets

### Database Optimization
- Index frequently queried columns
- Paginate search results (20 items per page)
- Limit chat history to recent 50 messages
- Archive old data to separate tables

---

## Monitoring & Analytics

### Backend Metrics
- API response times
- Error rates by endpoint
- Gemini API usage and costs
- Database query performance
- User sign-ups and subscription conversions

### iOS Analytics
- Screen view tracking
- Feature usage (search, chat, wardrobe)
- Subscription flow drop-off points
- Crash reporting
- User retention metrics

### Recommended Tools
- **Backend:** Sentry (error tracking), Datadog (APM)
- **iOS:** Firebase Analytics, Crashlytics
- **Business:** Mixpanel or Amplitude for product analytics

---

## Deployment Strategy

### Development Environment
- Local backend with SQLite
- Mock Gemini API responses for testing
- Stripe test mode

### Staging Environment
- Cloud-hosted backend with PostgreSQL
- Real Gemini API with test keys
- Stripe test mode
- TestFlight distribution for iOS

### Production Environment
- Auto-scaling backend infrastructure
- Managed PostgreSQL with backups
- Gemini production API keys
- Stripe live mode
- App Store release

### CI/CD Pipeline
1. Push to main → Run tests
2. Tests pass → Deploy to staging
3. Manual approval → Deploy to production
4. iOS: Automated build → TestFlight → App Store submission

---

## Cost Estimates (Monthly)

### Infrastructure
- Backend hosting: $20-50 (Railway/Heroku) or $10-30 (AWS/GCP)
- Database: $15-25 (managed PostgreSQL)
- Storage: $5-15 (S3/GCS for user images)
- CDN: $0-10 (based on traffic)

### APIs (estimated for 1000 active users)
- Google Gemini: $50-200 (depends on usage)
- Stripe: $0 + 2.9% + $0.30 per transaction
- Affiliate networks: $0 (earn commission instead)

### Services
- Domain: $10-15/year
- SSL: $0 (Let's Encrypt)
- Monitoring: $0-25 (free tiers available)
- Email: $0-10 (SendGrid free tier)

**Total:** ~$100-300/month for MVP with 1000 users

---

## Next Steps

1. Set up development environment and repositories
2. Create detailed wireframes and design mockups
3. Obtain API keys: Google Gemini, Stripe test mode
4. Begin Phase 1: Authentication foundation
5. Set up CI/CD pipeline
6. Establish monitoring and analytics

---

## Questions to Resolve

- [ ] Apple IAP vs Stripe for subscriptions? (Apple requires IAP for digital content)
- [ ] Which affiliate networks to prioritize?
- [ ] Hosting provider preference? (AWS, Google Cloud, Railway, Heroku)
- [ ] Analytics platform? (Firebase, Mixpanel, Amplitude)
- [ ] Product search: Build own database or use real-time Google Shopping API?
- [ ] Image storage: AWS S3 or Google Cloud Storage?
