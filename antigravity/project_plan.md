# PriceMatch AI - Project Plan (MVP Focus)

## Vision
Build the best AI-powered fashion discovery app on the iOS App Store that helps users find affordable, high-quality alternatives to any clothing or shoes through visual search with thorough, detailed product analysis.

## MVP Strategy
**Launch Fast, Iterate Smart:**
- **MVP:** Visual search + detailed descriptions + subscriptions + affiliate links
- **Phase 2:** AI chatbot for fashion advice
- **Phase 3:** Smart wardrobe analyzer

Focus on the core value proposition first: helping users find cheaper alternatives instantly.

## Target Market
Fashion-conscious iPhone users who want to:
- Find cheaper alternatives to expensive clothing instantly
- Get detailed, AI-powered analysis of clothing items
- Discover similar styles across multiple price points
- Shop smarter with personalized recommendations

## Revenue Model
- **Subscription**: $3.49/month or $39.99/year
- **Affiliate Marketing**: Commission on product purchases through the app

---

## MVP Features

### 1. Visual Search with Detailed Analysis (Core Feature)
**User Flow:**
1. User takes photo of clothing/shoes or uploads from camera roll
2. Image sent to Google Gemini Vision API
3. AI provides thorough analysis:
   - Item type and category
   - Style classification
   - Estimated brand/quality tier
   - Material and fabric details
   - Key features (patterns, embellishments, cut, fit)
   - Color palette
   - Season/occasion suitability
4. Backend searches for similar items at various price points
5. Results displayed Depop-style with detailed descriptions, similarity %, price, affiliate links

**What Makes Our Analysis "Thorough":**
- Not just "blue dress" but "cobalt blue midi dress, A-line silhouette, ruched bodice, flutter sleeves, lightweight polyester blend, cocktail/formal occasion"
- Price comparison: "Original item: ~$120, Our matches: $35-$85"
- Quality indicators: "Similar construction, comparable material grade"
- Style context: "Trending in spring 2025, pairs well with strappy heels"

**Technical Requirements:**
- iOS camera integration with image preprocessing
- Google Gemini Vision API with detailed prompts
- Product matching via Google Shopping API or affiliate network APIs
- Similarity scoring algorithm
- Affiliate link generation and click tracking
- Image storage (AWS S3 or Google Cloud Storage)

**Success Metrics:**
- Search accuracy >85%
- Results returned <5 seconds
- User finds satisfactory match in top 10 results
- >70% of users rate descriptions as "helpful" or "very helpful"

---

### 2. User Authentication & Accounts (MVP Core)
**Features:**
- Email/password signup and login
- Apple Sign-In (required for iOS App Store)
- Google Sign-In (optional)
- Password reset functionality
- User profile management

**Data to Store:**
- User credentials and profile info
- Search history (images searched, AI analysis results)
- Saved items and favorites
- Subscription status and payment info
- Browsing patterns for recommendations

**Technical Requirements:**
- Secure authentication (JWT tokens)
- PostgreSQL database for user data
- Privacy compliance (GDPR, CCPA)
- Data encryption at rest and in transit

---

### 3. Product Results & Affiliate Integration (MVP Core)
**Display Format (Depop-style):**
- Grid layout with product cards
- Each card shows:
  - Product thumbnail image
  - **Detailed description** (brand, item type, key features, material)
  - Price (current and original if discounted)
  - **Similarity percentage** to searched item
  - "Shop Now" button with affiliate link
  - Save/favorite heart icon

**Affiliate Strategy:**
- Integrate with affiliate networks: Amazon Associates, ShareASale, CJ Affiliate, Rakuten
- Track clicks and conversions
- Optimize for highest-converting merchants
- Transparent FTC-compliant affiliate disclosure

**Technical Requirements:**
- Affiliate API integrations
- Click tracking system with database logging
- Product database or real-time search
- Image caching via CDN
- Deep linking to merchant apps where available

---

### 4. Personalized Recommendations (MVP Core)
**Intelligence:**
- Analyze user's search history
- Identify style preferences and patterns (casual vs formal, color preferences, etc.)
- Track price range preferences
- Note favorite brands and categories
- Detect shopping frequency

**Recommendation Feed:**
- "For You" tab on home screen
- Based on browsing patterns and past searches
- Mix of similar items and gentle style expansion
- Prioritize items with affiliate links for monetization
- Refresh daily with new recommendations

**Technical Requirements:**
- User behavior tracking and analytics
- Recommendation algorithm (start simple: collaborative filtering based on similar users)
- Scheduled background job to refresh recommendations
- A/B testing framework for future optimization

---

### 5. Subscription & Monetization (MVP Core)
**Pricing:**
- **Free Tier**: 5 searches/day, view recommendations
- **Premium Monthly**: $3.49/month - unlimited searches, save unlimited favorites
- **Premium Annual**: $39.99/year (save 15%)
- Optional: 7-day free trial

**Technical Requirements:**
- **Apple IAP (recommended)**: Required by Apple for digital subscriptions
- Backend subscription management
- Webhook handling for subscription events
- Subscription status checking middleware
- Usage limit enforcement for free tier
- Graceful degradation when subscription expires
- Cancellation and refund handling

**Important:** Apple requires IAP for digital content (takes 30% cut). This is non-negotiable for App Store approval.

---

## Post-MVP Features (Phase 2 & 3)

### Phase 2: AI Fashion Chatbot
**Capabilities:**
- Answer fashion questions
- Recommend TikTok/Instagram influencers for style inspiration
- Provide trend forecasts and styling advice
- Help users describe items they want and trigger searches
- Conversational interface with Google Gemini

**Why Post-MVP:** Adds significant development time and ongoing API costs. MVP proves core value first.

---

### Phase 3: Smart Wardrobe Analyzer
**Capabilities:**
- Photograph entire wardrobe/closet
- AI identifies individual items
- Generate outfit suggestions by occasion (date night, casual, streetwear, formal, etc.)
- Save favorite combinations
- "Missing piece" suggestions

**Why Post-MVP:** Complex feature requiring multi-object detection, outfit algorithms, and additional UI. Launch core search feature first to validate market demand.

---

## Technical Architecture

### Backend Stack
**Recommended: Python + FastAPI**
- Pros: Excellent for AI/ML integration, async support, clean syntax, type hints
- Fast development with automatic API docs
- Easy Gemini API integration

**Alternative: Node.js + Express** if team has more JS experience

### Database
- **Primary: PostgreSQL** - User accounts, search history, favorites, subscriptions
- **Optional: Redis** - Session management, API response caching, rate limiting

### File Storage
- **AWS S3** or **Google Cloud Storage** for user-uploaded images
- CDN (CloudFront or Cloud CDN) for product images

### iOS Tech Stack
- **Language:** Swift 5.9+
- **UI Framework:** SwiftUI
- **Min iOS:** 16.0
- **Architecture:** MVVM
- **Networking:** URLSession with async/await
- **Image Loading:** AsyncImage or Kingfisher
- **Payment:** StoreKit 2 for Apple IAP

### AI & APIs
- **Google Gemini Vision API** (gemini-1.5-flash for cost, gemini-1.5-pro for quality)
- **Google Shopping API** or **Affiliate Network APIs** for product search
- **Apple StoreKit 2** for subscriptions

### Hosting
- **Backend:** Railway, Render, or Google Cloud Run (easy deployment)
- **Database:** Managed PostgreSQL (AWS RDS, Railway, or Supabase)
- **Storage:** AWS S3 or Google Cloud Storage

---

## MVP Development Timeline (10-12 Weeks)

### Phase 1: Foundation (Weeks 1-2)
**Backend:**
- [ ] Set up FastAPI project structure
- [ ] Configure PostgreSQL database
- [ ] Implement user authentication (email/password, Apple Sign-In)
- [ ] Design database schema
- [ ] Set up Google Gemini API integration
- [ ] Create basic API endpoints (auth, user profile)

**iOS:**
- [ ] Create Xcode project with SwiftUI
- [ ] Design app navigation (TabView structure)
- [ ] Build login/signup UI
- [ ] Implement Apple Sign-In and email auth
- [ ] Set up networking layer with async/await

**Deliverable:** Users can register, log in, and view empty home screen

---

### Phase 2: Visual Search Core (Weeks 3-5)
**Backend:**
- [ ] Build image upload endpoint with S3 storage
- [ ] Create detailed Gemini Vision prompt for thorough analysis
- [ ] Integrate Google Gemini Vision API
- [ ] Implement product search (start with Google Shopping API)
- [ ] Build similarity scoring algorithm
- [ ] Create product results endpoint with pagination

**iOS:**
- [ ] Implement camera capture with AVFoundation
- [ ] Build image picker and preview screen
- [ ] Design and build Depop-style product grid
- [ ] Implement AsyncImage with caching
- [ ] Display similarity percentages and detailed descriptions
- [ ] Add pull-to-refresh and infinite scroll

**Deliverable:** Users can photograph clothing and get detailed results with similar products

---

### Phase 3: Affiliate Integration (Weeks 6-7)
**Backend:**
- [ ] Sign up for affiliate networks (Amazon Associates, ShareASale)
- [ ] Integrate affiliate APIs
- [ ] Build affiliate link generator
- [ ] Implement click tracking system
- [ ] Add affiliate disclosure to API responses

**iOS:**
- [ ] Implement deep linking to affiliate products
- [ ] Add FTC-compliant affiliate disclosure UI
- [ ] Track link clicks before redirect
- [ ] Build in-app browser (SFSafariViewController) for affiliate links

**Deliverable:** Affiliate links functional with click tracking

---

### Phase 4: Favorites & Recommendations (Week 8)
**Backend:**
- [ ] Build favorites endpoints (save/unsave/list)
- [ ] Implement user behavior tracking
- [ ] Create basic recommendation algorithm
- [ ] Build recommendations endpoint
- [ ] Add background job for recommendation refresh

**iOS:**
- [ ] Add favorite button to product cards
- [ ] Build "Favorites" view
- [ ] Implement "For You" recommendation feed
- [ ] Add interaction tracking (views, clicks, saves)

**Deliverable:** Users can save favorites and see personalized recommendations

---

### Phase 5: Subscriptions & Paywall (Week 9)
**Backend:**
- [ ] Integrate Apple StoreKit Server API
- [ ] Build subscription status endpoint
- [ ] Implement usage limit checking (5 searches/day for free)
- [ ] Add subscription middleware to protect endpoints
- [ ] Create webhook handler for App Store notifications

**iOS:**
- [ ] Implement StoreKit 2 integration
- [ ] Build paywall UI (after 5 searches or on launch)
- [ ] Create subscription management screen
- [ ] Handle subscription purchase flow
- [ ] Implement usage limit UI (e.g., "3/5 searches today")
- [ ] Add "Upgrade to Premium" CTAs

**Deliverable:** Monetization active - subscriptions working, free tier limited

---

### Phase 6: Polish & Testing (Weeks 10-11)
- [ ] Comprehensive testing (unit, integration, end-to-end)
- [ ] Performance optimization:
  - Image compression and lazy loading
  - API response caching
  - Database query optimization
  - Reduce Gemini API call costs (prompt optimization, caching)
- [ ] UI/UX refinements based on internal testing
- [ ] Error handling and edge cases
- [ ] Loading states and animations
- [ ] Accessibility improvements (VoiceOver, Dynamic Type)

**Deliverable:** Polished, production-ready app

---

### Phase 7: Launch Prep (Week 12)
- [ ] Create App Store assets:
  - Screenshots for all device sizes
  - App preview video (optional but recommended)
  - App icon (multiple sizes)
  - App description optimized for ASO
  - Keywords research
- [ ] Write Privacy Policy and Terms of Service
- [ ] Set up analytics (Firebase or Mixpanel)
- [ ] Set up error tracking (Sentry or Crashlytics)
- [ ] TestFlight beta testing with 10-20 users
- [ ] Gather feedback and make final tweaks
- [ ] App Store submission

**Deliverable:** App submitted to App Store!

---

## API Endpoints (MVP)

### Authentication
```
POST   /api/auth/register          # Email/password signup
POST   /api/auth/login             # Email/password login
POST   /api/auth/apple             # Apple Sign-In
POST   /api/auth/refresh           # Refresh JWT token
GET    /api/users/me               # Get current user
PUT    /api/users/me               # Update profile
```

### Visual Search
```
POST   /api/search/image           # Upload image, get analysis + products
GET    /api/search/history         # Get user's search history
GET    /api/search/:id             # Get specific search results
```

### Favorites
```
POST   /api/favorites              # Save product
DELETE /api/favorites/:productId  # Remove from favorites
GET    /api/favorites              # Get all favorited items
```

### Recommendations
```
GET    /api/recommendations        # Get personalized product feed
POST   /api/recommendations/track  # Track user interaction
```

### Subscription
```
GET    /api/subscription/status    # Get current subscription status
POST   /api/subscription/webhook   # Apple App Store webhook
GET    /api/subscription/usage     # Get current usage (searches today)
```

### Products
```
POST   /api/products/:id/click     # Track affiliate link click
```

---

## Database Schema (MVP)

### users
```sql
id, email, password_hash, full_name, auth_provider,
subscription_status, subscription_expires_at, created_at, updated_at
```

### search_history
```sql
id, user_id, image_url, gemini_analysis (JSONB),
results_data (JSONB), created_at
```

### favorites
```sql
id, user_id, product_id, product_data (JSONB), created_at
UNIQUE(user_id, product_id)
```

### user_interactions
```sql
id, user_id, product_id, interaction_type (view/click/favorite),
product_category, product_price, created_at
```

### subscriptions (optional - can use App Store server-to-server notifications)
```sql
id, user_id, store_transaction_id, product_id,
expires_at, auto_renew_status, created_at
```

---

## Google Gemini Prompt Engineering

### Visual Search Prompt (MVP)
```python
def create_detailed_search_prompt(image):
    return """
    Analyze this clothing/shoe item in detail. Provide a thorough, comprehensive description.

    Respond in JSON format:
    {
        "item_type": "specific type (e.g., 'midi dress', 'high-top sneakers')",
        "style": "style category (e.g., 'casual', 'formal', 'streetwear')",
        "detailed_description": "comprehensive description (2-3 sentences covering silhouette, cut, fit, notable features)",
        "colors": ["primary color", "secondary color"],
        "material": "fabric/material type (if identifiable)",
        "key_features": ["feature 1", "feature 2", "feature 3"],
        "estimated_brand_tier": "luxury/mid-range/budget/fast-fashion",
        "season_occasion": "when to wear this",
        "search_terms": ["keyword 1", "keyword 2", "keyword 3"],
        "price_estimate": "estimated price range in USD"
    }

    Be specific and detailed. Users want thorough analysis.
    """
```

---

## Success Metrics (MVP)

### Acquisition (Months 1-3)
- **Target:** 1,000 downloads in first month
- **App Store conversion rate:** >25% (visitors → downloads)
- **Cost per install (if running ads):** <$2

### Activation
- **Sign-up completion:** >80% of downloads create account
- **First search completion:** >70% of sign-ups perform search
- **Time to first search:** <2 minutes

### Engagement
- **Daily Active Users (DAU):** Track growth
- **Searches per user per week:** Target 3-5 for free, 10+ for premium
- **Session length:** 3-5 minutes average
- **Favorite rate:** >30% of searches result in saved favorite

### Retention
- **Day 1 retention:** >50%
- **Day 7 retention:** >30%
- **Day 30 retention:** >15%
- **Weekly active users returning:** >60%

### Monetization
- **Free-to-paid conversion:** 2-5% (industry standard)
- **Monthly Recurring Revenue (MRR):** Target $500 by month 3
- **Annual Recurring Revenue (ARR):** Track annually subscribed users
- **Affiliate click-through rate:** >10% of product views
- **Affiliate conversion rate:** 1-3% of clicks → purchases

### Product Quality
- **Visual search accuracy:** >85% user satisfaction
- **Description helpfulness:** >70% rate as "helpful" or "very helpful"
- **App Store rating:** Target 4.5+ stars
- **Results speed:** <5 seconds for 90% of searches

---

## Cost Estimates (Monthly, MVP with 1,000 Active Users)

### Infrastructure
- **Backend hosting:** $15-30 (Railway/Render basic tier)
- **Database:** $10-20 (managed PostgreSQL)
- **Storage:** $5-10 (S3/GCS for user images)
- **CDN:** $0-5 (product image caching)

### APIs
- **Google Gemini Vision:** $30-100 (depends on usage, optimize with caching)
- **Apple IAP:** $0 + 30% of subscription revenue
- **Affiliate networks:** $0 (earn commission)

### Services
- **Domain:** $10-15/year ($1/month)
- **SSL:** $0 (Let's Encrypt or included in hosting)
- **Monitoring:** $0 (free tiers: Sentry, Firebase)
- **Email:** $0 (SendGrid free tier: 100 emails/day)

**Total MVP Costs:** ~$60-150/month

**Break-Even Analysis:**
- Need ~20 monthly subscribers ($3.49 × 20 = $69.80 gross, $48.86 after Apple's 30% cut)
- Or ~15 annual subscribers ($39.99 ÷ 12 × 15 = $49.99/month gross, $34.99 after Apple's cut)
- Plus affiliate commissions (variable)

---

## Risk Mitigation

### Technical Risks
- **Gemini API costs balloon:**
  - Solution: Aggressive caching, image compression, optimize prompts, use flash model
- **Search result quality poor:**
  - Solution: A/B test different search strategies, gather user feedback early
- **App Store rejection:**
  - Solution: Follow all guidelines carefully, especially IAP rules and affiliate disclosure

### Business Risks
- **User acquisition cost too high:**
  - Solution: Focus on organic growth, App Store SEO, social media, influencer partnerships
- **Low conversion to paid:**
  - Solution: Strong paywall after 5 searches, emphasize value, optimize pricing
- **Affiliate conversion too low:**
  - Solution: Test different networks, optimize product presentation, ensure link quality

### Legal Risks
- **Affiliate disclosure violations:**
  - Solution: Clear FTC-compliant disclosure on all affiliate content
- **User data privacy:**
  - Solution: GDPR/CCPA compliance, clear privacy policy, minimal data collection
- **Copyright on product images:**
  - Solution: Use official merchant images via APIs, proper attribution

---

## Next Steps to Start Development

### Week 0: Setup
1. **Accounts & Keys:**
   - [ ] Apple Developer account ($99/year)
   - [ ] Google Cloud account for Gemini API
   - [ ] Railway/Render account for hosting
   - [ ] GitHub repositories (backend + iOS)
   - [ ] Affiliate network accounts (Amazon Associates first)

2. **Design:**
   - [ ] Create basic wireframes for 5 key screens:
     - Login/Signup
     - Camera/Search screen
     - Results grid
     - Product detail
     - Paywall
   - [ ] Design app icon
   - [ ] Choose color scheme and fonts

3. **Planning:**
   - [ ] Set up project management (GitHub Projects, Linear, or Notion)
   - [ ] Create development environment setup guides
   - [ ] Finalize tech stack decisions

### Week 1: Start Building!
Begin Phase 1 (Foundation) as outlined in the timeline above.

---

## Key Decisions to Make Before Starting

- [ ] **Hosting provider:** Railway (easiest), Render, or Google Cloud Run?
- [ ] **Affiliate networks:** Start with Amazon Associates, add others later?
- [ ] **Analytics platform:** Firebase (free, easy) or Mixpanel (more powerful)?
- [ ] **Product search method:** Google Shopping API vs affiliate network APIs?
- [ ] **Free trial:** Offer 7-day free trial or just free tier with limits?

---

## Why This MVP Will Succeed

1. **Clear value proposition:** Find cheaper alternatives to any clothing item instantly
2. **Differentiation:** Thorough, detailed AI analysis - not just "similar items"
3. **Low initial cost:** ~$100/month to start, scales with users
4. **Fast time to market:** 10-12 weeks to launch
5. **Monetization from day 1:** Subscriptions + affiliate commissions
6. **Room to expand:** Chatbot and wardrobe features for Phase 2/3

Focus on nailing the core feature first, get users, gather feedback, then expand!
