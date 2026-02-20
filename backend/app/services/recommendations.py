"""Recommendation engine service with tier-based enhancements."""
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import httpx
import random
import hashlib
import time
import asyncio

from ..models import User, UserInteraction, SearchHistory, Favorite
from ..models.user import SUBSCRIPTION_TIERS
from ..schemas import Product, GeminiAnalysis
from ..config import settings


class SimpleCache:
    """Simple TTL cache to reduce API calls."""

    def __init__(self, ttl_seconds: int = 300):  # 5 minute default TTL
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """Set value in cache with current timestamp."""
        self._cache[key] = (value, time.time())

    def invalidate(self, key: str) -> bool:
        """Invalidate (remove) a specific cache entry. Returns True if key existed."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def invalidate_prefix(self, prefix: str) -> int:
        """Invalidate all cache entries with keys starting with prefix. Returns count."""
        keys_to_remove = [k for k in self._cache.keys() if k.startswith(prefix)]
        for key in keys_to_remove:
            del self._cache[key]
        return len(keys_to_remove)

    def clear_expired(self) -> None:
        """Remove expired entries."""
        current_time = time.time()
        expired = [k for k, (_, ts) in self._cache.items() if current_time - ts >= self._ttl]
        for key in expired:
            del self._cache[key]


class APIUsageTracker:
    """Track and limit SerpAPI usage to conserve monthly quota."""

    # Conservative daily limit (adjust based on your plan)
    # Free plan: ~100/month = ~3/day
    # Paid plans: adjust accordingly
    DAILY_LIMIT = 50  # Adjust this based on your SerpAPI plan

    def __init__(self):
        self._calls_today = 0
        self._last_reset_date = datetime.now().date()

    def _maybe_reset(self):
        """Reset counter if it's a new day."""
        today = datetime.now().date()
        if today > self._last_reset_date:
            print(f"DEBUG [API Tracker]: New day - resetting counter (was {self._calls_today})")
            self._calls_today = 0
            self._last_reset_date = today

    def can_make_call(self) -> bool:
        """Check if we're under the daily limit."""
        self._maybe_reset()
        return self._calls_today < self.DAILY_LIMIT

    def record_call(self):
        """Record an API call."""
        self._maybe_reset()
        self._calls_today += 1
        print(f"DEBUG [API Tracker]: Call #{self._calls_today}/{self.DAILY_LIMIT} today")

    def get_remaining(self) -> int:
        """Get remaining calls for today."""
        self._maybe_reset()
        return max(0, self.DAILY_LIMIT - self._calls_today)


# Global API usage tracker (shared across all services)
api_tracker = APIUsageTracker()


class RecommendationService:
    """Service for generating personalized recommendations with tier-based features."""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        # Cache for search results (2 HOUR TTL - aggressive caching)
        self._search_cache = SimpleCache(ttl_seconds=7200)
        # Cache for recommendation sections (1 HOUR TTL per user)
        self._sections_cache = SimpleCache(ttl_seconds=3600)
        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 1.0  # 1 second between requests

        # Diverse clothing categories for variety
        self.clothing_categories = [
            "hoodies",
            "sneakers",
            "jeans",
            "joggers",
            "t-shirts",
            "jackets",
            "sweatpants",
            "cargo pants",
            "oversized shirts",
            "bomber jackets",
            "high top sneakers",
            "cropped hoodies",
            "baggy jeans",
            "track pants",
        ]

        # Teen/young adult trending styles
        self.trending_styles = [
            "streetwear",
            "y2k fashion",
            "aesthetic",
            "vintage",
            "skater style",
            "gorpcore",
            "clean girl aesthetic",
            "old money style",
            "coastal granddaughter",
            "grunge",
        ]

    def _get_tier_config(self, tier: str) -> Dict[str, Any]:
        """Get recommendation configuration based on subscription tier."""
        configs = {
            "free": {
                "sections_count": 3,
                "products_per_section": 6,
                "include_exclusive": False,
                "include_luxury": False,
                "include_personalized": False,
                "label": "Free",
                "header_title": "Your Vibe Check",
                "header_subtitle": "Trending picks that match your aesthetic",
            },
            "basic": {
                "sections_count": 4,
                "products_per_section": 8,
                "include_exclusive": False,
                "include_luxury": False,
                "include_personalized": True,
                "label": "Basic",
                "header_title": "Curated For You",
                "header_subtitle": "Personalized recommendations based on your style",
            },
            "pro": {
                "sections_count": 5,
                "products_per_section": 10,
                "include_exclusive": True,
                "include_luxury": True,
                "include_personalized": True,
                "label": "Pro",
                "header_title": "Pro Picks",
                "header_subtitle": "Premium AI-curated looks just for you",
            },
            "unlimited": {
                "sections_count": 6,
                "products_per_section": 12,
                "include_exclusive": True,
                "include_luxury": True,
                "include_personalized": True,
                "label": "Unlimited",
                "header_title": "Unlimited Style",
                "header_subtitle": "Exclusive AI-curated recommendations with luxury picks",
            },
        }
        return configs.get(tier, configs["free"])

    def _get_user_preferences(self, user: User, db: Session) -> Dict[str, Any]:
        """Extract user preferences from their search history and favorites."""
        thirty_days_ago = datetime.now() - timedelta(days=30)

        # Get recent searches
        recent_searches = db.query(SearchHistory).filter(
            SearchHistory.user_id == user.id,
            SearchHistory.created_at >= thirty_days_ago
        ).order_by(desc(SearchHistory.created_at)).limit(20).all()

        # Get ALL favorites (liked items are important indicators)
        favorites = db.query(Favorite).filter(
            Favorite.user_id == user.id
        ).order_by(desc(Favorite.created_at)).limit(50).all()

        # Get interactions
        interactions = db.query(UserInteraction).filter(
            UserInteraction.user_id == user.id,
            UserInteraction.created_at >= thirty_days_ago
        ).all()

        # Initialize preference trackers with weights
        item_types = {}      # Types of clothing (hoodie, sneakers, jeans, etc.)
        colors = {}          # Preferred colors
        styles = {}          # Style categories (streetwear, vintage, etc.)
        brands = {}          # Preferred brands
        materials = {}       # Preferred materials
        price_ranges = []
        search_terms = []    # Actual search terms used
        key_features = []    # Key features from analyses

        # ===========================================
        # ANALYZE SEARCH HISTORY (Gemini Analysis)
        # ===========================================
        for search in recent_searches:
            # Weight: searches are intentional, so weight = 2
            weight = 2

            if search.search_type:
                item_types[search.search_type] = item_types.get(search.search_type, 0) + weight

            if search.gemini_analysis:
                analysis = search.gemini_analysis

                # Item type from analysis
                if analysis.get('item_type'):
                    item_type = analysis['item_type'].lower()
                    item_types[item_type] = item_types.get(item_type, 0) + weight

                # Colors
                if analysis.get('colors'):
                    for color in analysis.get('colors', []):
                        color_lower = color.lower()
                        colors[color_lower] = colors.get(color_lower, 0) + weight

                # Style
                if analysis.get('style'):
                    style = analysis['style'].lower()
                    styles[style] = styles.get(style, 0) + weight

                # Brand (if identified)
                if analysis.get('brand') and analysis['brand']:
                    brand = analysis['brand']
                    brands[brand] = brands.get(brand, 0) + weight

                # Material
                if analysis.get('material'):
                    material = analysis['material'].lower()
                    materials[material] = materials.get(material, 0) + weight

                # Search terms
                if analysis.get('search_terms'):
                    search_terms.extend(analysis.get('search_terms', [])[:3])

                # Key features
                if analysis.get('key_features'):
                    key_features.extend(analysis.get('key_features', [])[:3])

        # ===========================================
        # ANALYZE FAVORITES (Liked Items) - Higher weight!
        # ===========================================
        for favorite in favorites:
            # Weight: favorites are explicit likes, so weight = 3
            weight = 3

            if favorite.product_data:
                product = favorite.product_data

                # Category/Item type
                if product.get('category'):
                    cat = product['category'].lower()
                    item_types[cat] = item_types.get(cat, 0) + weight

                # Extract item type from title
                title = product.get('title', '').lower()
                for clothing_type in self.clothing_categories:
                    if clothing_type.lower() in title:
                        item_types[clothing_type] = item_types.get(clothing_type, 0) + weight

                # Brand from product
                if product.get('brand'):
                    brand = product['brand']
                    brands[brand] = brands.get(brand, 0) + weight

                # Price
                if product.get('price'):
                    try:
                        price_ranges.append(float(product['price']))
                    except (ValueError, TypeError):
                        pass

                # Extract colors from title (common color words)
                color_words = ['black', 'white', 'blue', 'red', 'green', 'pink', 'purple',
                              'grey', 'gray', 'navy', 'beige', 'brown', 'orange', 'yellow',
                              'cream', 'olive', 'burgundy', 'tan', 'khaki']
                for color in color_words:
                    if color in title:
                        colors[color] = colors.get(color, 0) + weight

                # Extract styles from title
                style_words = ['streetwear', 'vintage', 'casual', 'sporty', 'athletic',
                              'oversized', 'slim', 'baggy', 'cropped', 'high-waisted']
                for style in style_words:
                    if style in title:
                        styles[style] = styles.get(style, 0) + weight

        # ===========================================
        # ANALYZE INTERACTIONS
        # ===========================================
        for interaction in interactions:
            weight = 1
            if interaction.product_category:
                item_types[interaction.product_category] = item_types.get(interaction.product_category, 0) + weight
            if interaction.product_price:
                try:
                    price_ranges.append(float(interaction.product_price))
                except (ValueError, TypeError):
                    pass

        # ===========================================
        # COMPUTE TOP PREFERENCES
        # ===========================================
        def get_top_n(d: dict, n: int = 5) -> List[str]:
            """Get top N items sorted by frequency/weight."""
            sorted_items = sorted(d.items(), key=lambda x: x[1], reverse=True)
            return [item[0] for item in sorted_items[:n]]

        return {
            'item_types': item_types,
            'top_item_types': get_top_n(item_types, 5),
            'colors': colors,
            'top_colors': get_top_n(colors, 3),
            'styles': styles,
            'top_styles': get_top_n(styles, 3),
            'brands': brands,
            'top_brands': get_top_n(brands, 5),
            'materials': materials,
            'avg_price': sum(price_ranges) / len(price_ranges) if price_ranges else 75,
            'search_terms': list(set(search_terms))[:10],
            'key_features': list(set(key_features))[:10],
            'has_history': len(recent_searches) > 0,
            'has_favorites': len(favorites) > 0,
            'total_signals': len(recent_searches) + len(favorites) + len(interactions),
            # Legacy compatibility
            'categories': item_types,
        }

    async def _search_products(self, query: str, limit: int = 10) -> List[Product]:
        """Search for products using SerpApi with caching and daily limits."""
        if not settings.SERPAPI_API_KEY:
            return []

        # Check cache first
        cache_key = hashlib.md5(f"{query}:{limit}".encode()).hexdigest()
        cached_result = self._search_cache.get(cache_key)
        if cached_result is not None:
            print(f"DEBUG [Cache HIT]: '{query[:50]}...' - returning {len(cached_result)} cached products")
            return cached_result

        # Check daily API limit BEFORE making the call
        if not api_tracker.can_make_call():
            print(f"WARNING [API Limit]: Daily limit reached. Skipping search for '{query[:30]}'")
            return []

        try:
            # Rate limiting (1 second between requests)
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            if time_since_last < self._min_request_interval:
                await asyncio.sleep(self._min_request_interval - time_since_last)
            self._last_request_time = time.time()

            # Record this API call
            api_tracker.record_call()

            params = {
                "engine": "google_shopping",
                "q": query,
                "api_key": settings.SERPAPI_API_KEY,
                "google_domain": "google.com",
                "gl": "us",
                "hl": "en",
                "num": limit
            }

            response = await self.client.get("https://serpapi.com/search", params=params)

            # Handle rate limiting - return empty instead of raising
            if response.status_code == 429:
                print(f"WARNING: SerpApi rate limit hit for '{query[:30]}'. Using empty result.")
                self._search_cache.set(cache_key, [])  # Cache empty result briefly
                return []

            response.raise_for_status()
            data = response.json()

            shopping_results = data.get("shopping_results", [])
            products = []

            for i, item in enumerate(shopping_results):
                link = item.get("link") or item.get("product_link")
                if not link:
                    continue

                price_str = item.get("price", "0").replace("$", "").replace(",", "")
                try:
                    price = float(price_str)
                except ValueError:
                    price = 0.0

                orig_price_str = item.get("extracted_old_price")
                original_price = float(orig_price_str) if orig_price_str else None

                products.append(Product(
                    id=item.get("product_id", f"rec_{i}_{random.randint(1000, 9999)}"),
                    title=item.get("title", "Product"),
                    description=item.get("snippet", ""),
                    price=price,
                    original_price=original_price,
                    currency="USD",
                    image_url=item.get("thumbnail", "https://via.placeholder.com/300"),
                    merchant=item.get("source", "Unknown"),
                    affiliate_link=link,
                    similarity_percentage=random.randint(80, 95),
                    brand=item.get("source"),
                    category=query.split()[0] if query else "fashion"
                ))

            # Cache the results
            self._search_cache.set(cache_key, products)
            print(f"DEBUG [Cache MISS]: '{query[:50]}...' - cached {len(products)} products")

            return products

        except Exception as e:
            print(f"Error fetching recommendations: {e}")
            # Cache empty result to prevent repeated failed calls
            self._search_cache.set(cache_key, [])
            return []

    async def _get_varied_products(self, base_query: str, categories: List[str], limit_per_category: int = 3) -> List[Product]:
        """Get a varied mix of products - OPTIMIZED to use single query."""
        # Instead of multiple queries, combine into one smart query
        selected_cats = random.sample(categories, min(len(categories), 3))
        combined_query = f"{base_query} {' '.join(selected_cats)}"
        products = await self._search_products(combined_query, limit_per_category * 3)
        random.shuffle(products)
        return products

    def _get_fallback_products(self) -> List[Dict[str, Any]]:
        """Return curated fallback products when API is unavailable."""
        # Static placeholder products to show when rate limited
        return [
            {
                "id": "fallback_1",
                "title": "Classic Streetwear Hoodie",
                "description": "Comfortable oversized hoodie perfect for everyday wear",
                "price": 45.99,
                "currency": "USD",
                "image_url": "https://via.placeholder.com/300x300?text=Hoodie",
                "merchant": "Style Shop",
                "affiliate_link": "#",
                "similarity_percentage": 90,
                "brand": "Style Shop",
                "category": "hoodie"
            },
            {
                "id": "fallback_2",
                "title": "Trendy Sneakers",
                "description": "Versatile sneakers that go with any outfit",
                "price": 89.99,
                "currency": "USD",
                "image_url": "https://via.placeholder.com/300x300?text=Sneakers",
                "merchant": "Shoe Hub",
                "affiliate_link": "#",
                "similarity_percentage": 88,
                "brand": "Shoe Hub",
                "category": "sneakers"
            },
            {
                "id": "fallback_3",
                "title": "Baggy Jeans",
                "description": "Relaxed fit denim with vintage vibes",
                "price": 59.99,
                "currency": "USD",
                "image_url": "https://via.placeholder.com/300x300?text=Jeans",
                "merchant": "Denim Co",
                "affiliate_link": "#",
                "similarity_percentage": 85,
                "brand": "Denim Co",
                "category": "jeans"
            }
        ]

    async def _generate_personalized_style_recommendations(
        self,
        prefs: Dict[str, Any],
        tier_config: Dict[str, Any]
    ) -> List[Product]:
        """
        Generate highly personalized recommendations based on user's search history and favorites.
        This powers the "Based on Your Style" section with AI-driven personalization.
        """
        all_products = []
        used_ids = set()
        products_per_section = tier_config.get("products_per_section", 8)

        # Strategy: Create diverse queries from user preferences
        # Each query combines different aspects of their style profile

        queries_to_run = []

        # ===========================================
        # STRATEGY 1: Top item types with preferred colors
        # ===========================================
        top_item_types = prefs.get('top_item_types', [])[:4]
        top_colors = prefs.get('top_colors', [])[:2]

        for item_type in top_item_types:
            if top_colors:
                # Combine item type with top color
                color = random.choice(top_colors)
                queries_to_run.append(f"{color} {item_type}")
            else:
                queries_to_run.append(f"trendy {item_type}")

        # ===========================================
        # STRATEGY 2: Preferred styles with variety
        # ===========================================
        top_styles = prefs.get('top_styles', [])[:2]
        for style in top_styles:
            # Pick a random category to pair with the style
            if top_item_types:
                item = random.choice(top_item_types)
                queries_to_run.append(f"{style} {item}")
            else:
                queries_to_run.append(f"{style} clothing")

        # ===========================================
        # STRATEGY 3: Brand-based recommendations
        # ===========================================
        top_brands = prefs.get('top_brands', [])[:3]
        for brand in top_brands:
            # Search for items from brands they like
            if top_item_types:
                item = random.choice(top_item_types)
                queries_to_run.append(f"{brand} {item}")
            else:
                queries_to_run.append(f"{brand} fashion")

        # ===========================================
        # STRATEGY 4: Use actual search terms they've used
        # ===========================================
        search_terms = prefs.get('search_terms', [])[:3]
        for term in search_terms:
            if term and len(term) > 3:
                queries_to_run.append(term)

        # ===========================================
        # STRATEGY 5: Price-aware recommendations
        # ===========================================
        avg_price = prefs.get('avg_price', 75)
        if avg_price < 50:
            # User likes budget items
            if top_item_types:
                queries_to_run.append(f"affordable {top_item_types[0]} under $50")
        elif avg_price > 150:
            # User likes premium items
            if top_item_types:
                queries_to_run.append(f"premium {top_item_types[0]}")

        # ===========================================
        # FALLBACK: If no preferences, use trending items
        # ===========================================
        if not queries_to_run:
            queries_to_run = [
                "streetwear hoodie",
                "trendy sneakers",
                "aesthetic jeans",
                "graphic tee"
            ]

        # AGGRESSIVE OPTIMIZATION: Limit to just 2-3 queries max
        queries_to_run = list(dict.fromkeys(queries_to_run))[:3]

        print(f"DEBUG [Personalized]: Running {len(queries_to_run)} queries (limited to conserve API)")
        print(f"DEBUG [Personalized]: Queries: {queries_to_run}")

        # ===========================================
        # Execute queries and collect products
        # ===========================================
        for query in queries_to_run:
            try:
                prods = await self._search_products(query, 4)
                for product in prods:
                    if product.id not in used_ids:
                        # Mark these as personalized matches with higher similarity
                        product.similarity_percentage = random.randint(85, 98)
                        all_products.append(product)
                        used_ids.add(product.id)

                        # Stop if we have enough products
                        if len(all_products) >= products_per_section * 2:
                            break
            except Exception as e:
                print(f"DEBUG [Personalized]: Error searching '{query}': {e}")
                continue

            if len(all_products) >= products_per_section * 2:
                break

        # Shuffle for variety but keep some relevance order
        if len(all_products) > products_per_section:
            # Keep the first few (most relevant) and shuffle the rest
            top_products = all_products[:products_per_section // 2]
            remaining = all_products[products_per_section // 2:]
            random.shuffle(remaining)
            all_products = top_products + remaining

        print(f"DEBUG [Personalized]: Found {len(all_products)} personalized products")

        return all_products

    async def get_recommendations_for_user(
        self,
        user: User,
        db: Session,
        limit: int = 20
    ) -> List[Product]:
        """Generate personalized product recommendations."""
        prefs = self._get_user_preferences(user, db)

        if not prefs['has_history']:
            # Default recommendations for new users - varied
            return await self._get_varied_products("trending teen", self.clothing_categories[:6], 4)

        # Build search query from preferences
        query_parts = []
        if prefs['categories']:
            top_category = max(prefs['categories'], key=prefs['categories'].get)
            query_parts.append(top_category)
        if prefs['colors']:
            top_color = max(prefs['colors'], key=prefs['colors'].get)
            query_parts.append(top_color)
        if prefs['styles']:
            top_style = max(prefs['styles'], key=prefs['styles'].get)
            query_parts.append(top_style)

        query = " ".join(query_parts) if query_parts else "fashion clothing"
        return await self._search_products(query, limit)

    async def get_recommendation_sections(
        self,
        user: User,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Generate sectioned recommendations for the For You page with tier-based features."""
        # Check user-specific cache first (10 minute TTL)
        cache_key = f"sections:{user.id}:{user.subscription_tier or 'free'}"
        cached_sections = self._sections_cache.get(cache_key)
        if cached_sections is not None:
            print(f"DEBUG [Sections Cache HIT]: User {user.id} - returning cached sections")
            return cached_sections

        print(f"DEBUG [Sections Cache MISS]: User {user.id} - generating new sections")

        prefs = self._get_user_preferences(user, db)
        tier = user.subscription_tier or "free"
        tier_config = self._get_tier_config(tier)
        sections = []

        # Add tier metadata to response
        tier_metadata = {
            "user_tier": tier,
            "tier_label": tier_config["label"],
            "header_title": tier_config["header_title"],
            "header_subtitle": tier_config["header_subtitle"],
            "is_premium": tier in ["basic", "pro", "unlimited"],
        }

        # Section 1: Trending Now - SINGLE consolidated query instead of 4 separate ones
        trending_style = random.choice(self.trending_styles)
        # One smart query that covers multiple categories
        trending_query = f"trending {trending_style} fashion hoodie sneakers 2025"
        trending_products = await self._search_products(trending_query, 12)

        if trending_products:
            random.shuffle(trending_products)
            sections.append({
                "title": "Trending Now",
                "subtitle": f"🔥 Hot {trending_style} picks for Gen Z",
                "products": [p.dict() for p in trending_products[:tier_config["products_per_section"]]]
            })

        # Section 2: Based on Your Style - AI-PERSONALIZED from history & favorites
        if prefs['has_history'] or prefs['has_favorites']:
            style_products = await self._generate_personalized_style_recommendations(prefs, tier_config)

            if style_products:
                # Build a personalized subtitle
                subtitle_parts = []
                if prefs['top_colors']:
                    subtitle_parts.append(prefs['top_colors'][0])
                if prefs['top_styles']:
                    subtitle_parts.append(prefs['top_styles'][0])

                if subtitle_parts:
                    subtitle = f"✨ Curated for your {' & '.join(subtitle_parts)} aesthetic"
                else:
                    subtitle = "✨ Curated picks matching your unique vibe"

                sections.append({
                    "title": "Based on Your Style",
                    "subtitle": subtitle,
                    "products": [p.dict() for p in style_products[:tier_config["products_per_section"]]]
                })
        else:
            # New user - SINGLE query for variety
            variety_query = "teen streetwear hoodie sneakers jeans essentials"
            variety_products = await self._search_products(variety_query, 12)

            if variety_products:
                random.shuffle(variety_products)
                sections.append({
                    "title": "Start Your Collection",
                    "subtitle": "Essential pieces to build your wardrobe",
                    "products": [p.dict() for p in variety_products[:tier_config["products_per_section"]]]
                })

        # Section 3: Deals For You - SINGLE query instead of 4
        deal_query = "sale fashion hoodie sneakers jeans under $60"
        deal_products = await self._search_products(deal_query, 12)

        if deal_products:
            random.shuffle(deal_products)
            sections.append({
                "title": "Deals For You",
                "subtitle": "🏷️ Great prices on fire pieces",
                "products": [p.dict() for p in deal_products[:tier_config["products_per_section"]]]
            })

        # Section 4: Basic+ tier - Fresh Drops (SINGLE query)
        if tier in ["basic", "pro", "unlimited"]:
            fresh_query = "new release 2025 sneakers hoodie streetwear"
            fresh_products = await self._search_products(fresh_query, 12)

            if fresh_products:
                random.shuffle(fresh_products)
                sections.append({
                    "title": "Fresh Drops",
                    "subtitle": "✨ Just dropped this week",
                    "products": [p.dict() for p in fresh_products[:tier_config["products_per_section"]]]
                })

        # Section 5: Pro+ tier - Luxury Picks (SINGLE query)
        if tier_config["include_luxury"]:
            luxury_query = "designer premium luxury streetwear sneakers hoodie"
            luxury_products = await self._search_products(luxury_query, 12)

            if luxury_products:
                random.shuffle(luxury_products)
                sections.append({
                    "title": "Luxury Picks",
                    "subtitle": "👑 Premium pieces worth the investment",
                    "products": [p.dict() for p in luxury_products[:tier_config["products_per_section"]]]
                })

        # Section 6: Unlimited tier - Exclusive Finds (SINGLE query)
        if tier == "unlimited":
            exclusive_query = "limited edition exclusive rare vintage sneakers hoodie"
            exclusive_products = await self._search_products(exclusive_query, 12)

            if exclusive_products:
                random.shuffle(exclusive_products)
                sections.append({
                    "title": "Exclusive Finds",
                    "subtitle": "💎 Rare pieces for the true collector",
                    "products": [p.dict() for p in exclusive_products[:tier_config["products_per_section"]]]
                })

        # Fallback if no sections generated (likely due to rate limiting)
        if not sections:
            # Try ONE last search (not 4!)
            default_query = "trendy teen fashion hoodie sneakers jeans"
            default_products = await self._search_products(default_query, 10)

            if default_products:
                random.shuffle(default_products)
                sections.append({
                    "title": "Discover",
                    "subtitle": "Start exploring styles",
                    "products": [p.dict() for p in default_products[:8]]
                })
            else:
                # Complete fallback - return curated static data
                sections.append({
                    "title": "Coming Soon",
                    "subtitle": "Personalized recommendations are being prepared for you",
                    "products": self._get_fallback_products(),
                    "_rate_limited": True
                })

        # Add tier metadata to first section or as separate field
        if sections:
            sections[0]["_tier_metadata"] = tier_metadata

        # Cache the sections for this user
        self._sections_cache.set(cache_key, sections)
        print(f"DEBUG [Sections Cache SET]: User {user.id} - cached {len(sections)} sections")

        return sections


    def invalidate_user_recommendations(self, user_id: int) -> bool:
        """
        Invalidate cached recommendations for a specific user.
        Call this after a user performs a search to ensure their
        'For You' section reflects their latest activity.

        Returns True if any cache was invalidated.
        """
        # Clear any cached sections for this user (matches all tier variants)
        count = self._sections_cache.invalidate_prefix(f"sections:{user_id}:")
        if count > 0:
            print(f"DEBUG [Cache Invalidated]: User {user_id} - cleared {count} recommendation cache entries")
            return True
        return False


# Singleton instance
recommendation_service = RecommendationService()
