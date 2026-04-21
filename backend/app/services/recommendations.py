"""Recommendation engine service with tier-based enhancements."""
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import httpx
import random
import hashlib
import time
import asyncio

from ..models import User, UserInteraction, SearchHistory, Favorite, WardrobeItem
from ..models.user import SUBSCRIPTION_TIERS
from ..schemas import Product, GeminiAnalysis
from ..config import settings

logger = logging.getLogger(__name__)


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
        """Extract user preferences from onboarding, search history, and favorites."""
        thirty_days_ago = datetime.now() - timedelta(days=30)

        # ===========================================
        # ONBOARDING PREFERENCES (highest priority - explicit user choices)
        # ===========================================
        onboarding_styles = getattr(user, 'style_preferences', None) or []
        onboarding_gender = getattr(user, 'gender_preference', None) or "either"

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
        # APPLY ONBOARDING STYLES (weight = 5, highest priority)
        # ===========================================
        for style in onboarding_styles:
            style_lower = style.lower()
            styles[style_lower] = styles.get(style_lower, 0) + 5

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
        # ANALYZE WARDROBE ITEMS (HIGH PRIORITY - things user actually owns!)
        # ===========================================
        wardrobe_items = db.query(WardrobeItem).filter(
            WardrobeItem.user_id == user.id
        ).limit(50).all()

        wardrobe_item_types = {}  # Separate tracking for wardrobe-specific preferences
        wardrobe_colors = {}
        wardrobe_styles = {}
        wardrobe_genders = {"menswear": 0, "womenswear": 0, "unisex": 0}  # Track gender from items

        for wardrobe_item in wardrobe_items:
            # Weight: wardrobe items are things they ACTUALLY OWN, so weight = 4 (very high!)
            weight = 4

            # Item type (top, bottom, shoes, etc.)
            if wardrobe_item.item_type:
                item_type = wardrobe_item.item_type.lower()
                item_types[item_type] = item_types.get(item_type, 0) + weight
                wardrobe_item_types[item_type] = wardrobe_item_types.get(item_type, 0) + weight

            # Subtype for more specific matching (t-shirt, jeans, sneakers)
            if wardrobe_item.item_subtype:
                subtype = wardrobe_item.item_subtype.lower()
                item_types[subtype] = item_types.get(subtype, 0) + weight
                wardrobe_item_types[subtype] = wardrobe_item_types.get(subtype, 0) + weight

            # Colors from wardrobe
            if wardrobe_item.color:
                color = wardrobe_item.color.lower()
                colors[color] = colors.get(color, 0) + weight
                wardrobe_colors[color] = wardrobe_colors.get(color, 0) + weight

            # Style tags from AI analysis
            if wardrobe_item.style_tags:
                for tag in wardrobe_item.style_tags:
                    tag_lower = tag.lower()
                    styles[tag_lower] = styles.get(tag_lower, 0) + weight
                    wardrobe_styles[tag_lower] = wardrobe_styles.get(tag_lower, 0) + weight
                    # Also track gender from style tags
                    if 'menswear' in tag_lower or 'mens' in tag_lower or "men's" in tag_lower:
                        wardrobe_genders["menswear"] += weight
                    elif 'womenswear' in tag_lower or 'womens' in tag_lower or "women's" in tag_lower:
                        wardrobe_genders["womenswear"] += weight

            # Track gender field if available (new wardrobe items will have this)
            if hasattr(wardrobe_item, 'gender') and wardrobe_item.gender:
                gender = wardrobe_item.gender.lower()
                if gender in wardrobe_genders:
                    wardrobe_genders[gender] += weight

            # Material preferences
            if wardrobe_item.material:
                material = wardrobe_item.material.lower()
                materials[material] = materials.get(material, 0) + weight

            # Brand if known
            if wardrobe_item.brand:
                brand = wardrobe_item.brand
                brands[brand] = brands.get(brand, 0) + weight

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
            'total_signals': len(recent_searches) + len(favorites) + len(interactions) + len(wardrobe_items),
            # Onboarding preferences
            'onboarding_styles': onboarding_styles,
            'onboarding_gender': onboarding_gender,
            'has_onboarding': len(onboarding_styles) > 0,
            # Wardrobe-based preferences (high value signals!)
            'wardrobe_item_types': wardrobe_item_types,
            'top_wardrobe_types': get_top_n(wardrobe_item_types, 5),
            'wardrobe_colors': wardrobe_colors,
            'top_wardrobe_colors': get_top_n(wardrobe_colors, 3),
            'wardrobe_styles': wardrobe_styles,
            'top_wardrobe_styles': get_top_n(wardrobe_styles, 3),
            'wardrobe_genders': wardrobe_genders,
            'wardrobe_dominant_gender': max(wardrobe_genders, key=wardrobe_genders.get) if any(wardrobe_genders.values()) else None,
            'has_wardrobe': len(wardrobe_items) > 0,
            'wardrobe_count': len(wardrobe_items),
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
            return cached_result

        # Check daily API limit BEFORE making the call
        if not api_tracker.can_make_call():
            logger.warning("Daily API limit reached. Skipping search.")
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
                logger.warning("SerpApi rate limit hit. Using empty result.")
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

            return products

        except Exception as e:
            logger.error(f"Error fetching recommendations: {e}")
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
        tier_config: Dict[str, Any],
        gender_prefix: str = ""
    ) -> List[Product]:
        """
        Generate highly personalized recommendations based on onboarding, search history, and favorites.
        This powers the "Based on Your Style" section with AI-driven personalization.
        """
        all_products = []
        used_ids = set()
        products_per_section = tier_config.get("products_per_section", 8)

        # Strategy: Create diverse queries from user preferences
        # Each query combines different aspects of their style profile

        queries_to_run = []

        # ===========================================
        # STRATEGY 0: WARDROBE-BASED (highest priority - what they actually own!)
        # ===========================================
        top_wardrobe_types = prefs.get('top_wardrobe_types', [])
        top_wardrobe_colors = prefs.get('top_wardrobe_colors', [])
        top_wardrobe_styles = prefs.get('top_wardrobe_styles', [])

        # If user has wardrobe items, prioritize finding similar items
        if top_wardrobe_types:
            for item_type in top_wardrobe_types[:3]:
                if top_wardrobe_colors:
                    color = random.choice(top_wardrobe_colors)
                    queries_to_run.append(f"{gender_prefix}{color} {item_type}")
                elif top_wardrobe_styles:
                    style = random.choice(top_wardrobe_styles)
                    queries_to_run.append(f"{gender_prefix}{style} {item_type}")
                else:
                    queries_to_run.append(f"{gender_prefix}trendy {item_type}")

        # ===========================================
        # STRATEGY 0.5: ONBOARDING STYLES (high priority!)
        # ===========================================
        onboarding_styles = prefs.get('onboarding_styles', [])
        if onboarding_styles:
            # User explicitly selected these styles during onboarding
            for style in onboarding_styles[:2]:
                queries_to_run.append(f"{gender_prefix}{style} fashion clothing")

        # ===========================================
        # STRATEGY 1: Top item types with preferred colors
        # ===========================================
        top_item_types = prefs.get('top_item_types', [])[:4]
        top_colors = prefs.get('top_colors', [])[:2]

        for item_type in top_item_types:
            if top_colors:
                # Combine item type with top color
                color = random.choice(top_colors)
                queries_to_run.append(f"{gender_prefix}{color} {item_type}")
            else:
                queries_to_run.append(f"{gender_prefix}trendy {item_type}")

        # ===========================================
        # STRATEGY 2: Preferred styles with variety
        # ===========================================
        top_styles = prefs.get('top_styles', [])[:2]
        for style in top_styles:
            # Pick a random category to pair with the style
            if top_item_types:
                item = random.choice(top_item_types)
                queries_to_run.append(f"{gender_prefix}{style} {item}")
            else:
                queries_to_run.append(f"{gender_prefix}{style} clothing")

        # ===========================================
        # STRATEGY 3: Brand-based recommendations
        # ===========================================
        top_brands = prefs.get('top_brands', [])[:3]
        for brand in top_brands:
            # Search for items from brands they like
            if top_item_types:
                item = random.choice(top_item_types)
                queries_to_run.append(f"{gender_prefix}{brand} {item}")
            else:
                queries_to_run.append(f"{gender_prefix}{brand} fashion")

        # ===========================================
        # STRATEGY 4: Use actual search terms they've used
        # ===========================================
        search_terms = prefs.get('search_terms', [])[:3]
        for term in search_terms:
            if term and len(term) > 3:
                queries_to_run.append(f"{gender_prefix}{term}")

        # ===========================================
        # STRATEGY 5: Price-aware recommendations
        # ===========================================
        avg_price = prefs.get('avg_price', 75)
        if avg_price < 50:
            # User likes budget items
            if top_item_types:
                queries_to_run.append(f"{gender_prefix}affordable {top_item_types[0]} under $50")
        elif avg_price > 150:
            # User likes premium items
            if top_item_types:
                queries_to_run.append(f"{gender_prefix}premium {top_item_types[0]}")

        # ===========================================
        # FALLBACK: If no preferences, use onboarding styles or trending items
        # ===========================================
        if not queries_to_run:
            if onboarding_styles:
                style = random.choice(onboarding_styles)
                queries_to_run = [
                    f"{gender_prefix}{style} hoodie",
                    f"{gender_prefix}{style} sneakers",
                    f"{gender_prefix}{style} jeans",
                ]
            else:
                queries_to_run = [
                    f"{gender_prefix}streetwear hoodie",
                    f"{gender_prefix}trendy sneakers",
                    f"{gender_prefix}aesthetic jeans",
                    f"{gender_prefix}graphic tee"
                ]

        # AGGRESSIVE OPTIMIZATION: Limit to just 2-3 queries max
        queries_to_run = list(dict.fromkeys(queries_to_run))[:3]

        # Execute queries and collect products
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
                logger.error(f"Error searching for personalized recommendations: {e}")
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
            return cached_sections

        prefs = self._get_user_preferences(user, db)
        tier = user.subscription_tier or "free"
        tier_config = self._get_tier_config(tier)
        sections = []

        # Get gender prefix from onboarding preferences OR detect from wardrobe
        gender_pref = prefs.get('onboarding_gender', 'either')
        gender_prefix = ""
        if gender_pref == "male":
            gender_prefix = "men's "
        elif gender_pref == "female":
            gender_prefix = "women's "
        elif gender_pref == "either":
            # Try to detect gender from wardrobe items
            wardrobe_dominant_gender = prefs.get('wardrobe_dominant_gender')
            wardrobe_genders = prefs.get('wardrobe_genders', {})

            # Check wardrobe gender tracking first (most reliable)
            if wardrobe_dominant_gender == "menswear" and wardrobe_genders.get("menswear", 0) > wardrobe_genders.get("womenswear", 0):
                gender_prefix = "men's "
            elif wardrobe_dominant_gender == "womenswear" and wardrobe_genders.get("womenswear", 0) > wardrobe_genders.get("menswear", 0):
                gender_prefix = "women's "
            else:
                # Fallback: check style tags for gender keywords
                wardrobe_styles = prefs.get('wardrobe_styles', {})
                wardrobe_types = prefs.get('wardrobe_item_types', {})
                all_wardrobe_terms = list(wardrobe_styles.keys()) + list(wardrobe_types.keys())
                all_terms_lower = ' '.join(all_wardrobe_terms).lower()

                mens_keywords = ['menswear', "men's", 'mens', 'masculine', 'male', 'boyfriend']
                womens_keywords = ['womenswear', "women's", 'womens', 'feminine', 'female', 'girly']

                mens_score = sum(1 for kw in mens_keywords if kw in all_terms_lower)
                womens_score = sum(1 for kw in womens_keywords if kw in all_terms_lower)

                if mens_score > womens_score:
                    gender_prefix = "men's "
                elif womens_score > mens_score:
                    gender_prefix = "women's "

        # Get onboarding styles for personalization
        onboarding_styles = prefs.get('onboarding_styles', [])

        # Add tier metadata to response
        tier_metadata = {
            "user_tier": tier,
            "tier_label": tier_config["label"],
            "header_title": tier_config["header_title"],
            "header_subtitle": tier_config["header_subtitle"],
            "is_premium": tier in ["basic", "pro", "unlimited"],
        }

        # Section 1: Trending Now - use onboarding styles if available
        if onboarding_styles:
            # Use user's preferred styles
            trending_style = random.choice(onboarding_styles)
        else:
            trending_style = random.choice(self.trending_styles)

        # One smart query that covers multiple categories - WITH GENDER PREFIX
        trending_query = f"{gender_prefix}trending {trending_style} fashion hoodie sneakers 2026"
        trending_products = await self._search_products(trending_query, 12)

        if trending_products:
            random.shuffle(trending_products)
            sections.append({
                "title": "Trending Now",
                "subtitle": f"Popular {trending_style} styles right now",
                "products": [p.dict() for p in trending_products[:tier_config["products_per_section"]]]
            })

        # Section 2: Similar to Your Closet - items matching what user owns (PRIORITY!)
        if prefs.get('has_wardrobe') and prefs.get('wardrobe_count', 0) >= 1:
            # Build query from wardrobe items
            wardrobe_types = prefs.get('top_wardrobe_types', [])[:3]
            wardrobe_colors = prefs.get('top_wardrobe_colors', [])[:2]
            wardrobe_styles = prefs.get('top_wardrobe_styles', [])[:2]

            closet_query_parts = []
            if wardrobe_types:
                closet_query_parts.extend(wardrobe_types)
            if wardrobe_colors:
                closet_query_parts.append(random.choice(wardrobe_colors))
            if wardrobe_styles:
                closet_query_parts.append(random.choice(wardrobe_styles))

            if closet_query_parts:
                closet_query = f"{gender_prefix}{' '.join(closet_query_parts)} fashion"
                closet_products = await self._search_products(closet_query, 12)

                if closet_products:
                    random.shuffle(closet_products)
                    # Build descriptive subtitle
                    if wardrobe_types:
                        type_str = wardrobe_types[0]
                        subtitle = f"More {type_str}s you'll love"
                    else:
                        subtitle = "Matching your wardrobe style"

                    sections.append({
                        "title": "Similar to Your Closet",
                        "subtitle": subtitle,
                        "products": [p.dict() for p in closet_products[:tier_config["products_per_section"]]]
                    })

        # Section 3: Based on Your Style - AI-PERSONALIZED from history, favorites, AND onboarding
        if prefs['has_history'] or prefs['has_favorites'] or prefs.get('has_onboarding'):
            style_products = await self._generate_personalized_style_recommendations(prefs, tier_config, gender_prefix)

            if style_products:
                # Build a personalized subtitle
                subtitle_parts = []
                if prefs['top_colors']:
                    subtitle_parts.append(prefs['top_colors'][0])
                if prefs['top_styles']:
                    subtitle_parts.append(prefs['top_styles'][0])

                if subtitle_parts:
                    subtitle = f"Curated for your {' & '.join(subtitle_parts)} style"
                else:
                    subtitle = "Curated picks based on your preferences"

                sections.append({
                    "title": "Based on Your Style",
                    "subtitle": subtitle,
                    "products": [p.dict() for p in style_products[:tier_config["products_per_section"]]]
                })
        elif not prefs.get('has_wardrobe'):
            # New user with no preferences - use gender prefix if available
            variety_query = f"{gender_prefix}teen streetwear hoodie sneakers jeans essentials"
            variety_products = await self._search_products(variety_query, 12)

            if variety_products:
                random.shuffle(variety_products)
                sections.append({
                    "title": "Start Your Collection",
                    "subtitle": "Essential pieces to build your wardrobe",
                    "products": [p.dict() for p in variety_products[:tier_config["products_per_section"]]]
                })

        # Section 3: Deals For You - with gender preference
        deal_query = f"{gender_prefix}sale fashion hoodie sneakers jeans under $60"
        deal_products = await self._search_products(deal_query, 12)

        if deal_products:
            random.shuffle(deal_products)
            sections.append({
                "title": "Deals For You",
                "subtitle": "🏷️ Great prices on fire pieces",
                "products": [p.dict() for p in deal_products[:tier_config["products_per_section"]]]
            })

        # Section 4: Basic+ tier - Fresh Drops (with gender preference)
        if tier in ["basic", "pro", "unlimited"]:
            fresh_query = f"{gender_prefix}new release 2026 sneakers hoodie streetwear"
            fresh_products = await self._search_products(fresh_query, 12)

            if fresh_products:
                random.shuffle(fresh_products)
                sections.append({
                    "title": "Fresh Drops",
                    "subtitle": "Just dropped this week",
                    "products": [p.dict() for p in fresh_products[:tier_config["products_per_section"]]]
                })

        # Section 5: Pro+ tier - Luxury Picks (with gender preference)
        if tier_config["include_luxury"]:
            luxury_query = f"{gender_prefix}designer premium luxury streetwear sneakers hoodie"
            luxury_products = await self._search_products(luxury_query, 12)

            if luxury_products:
                random.shuffle(luxury_products)
                sections.append({
                    "title": "Luxury Picks",
                    "subtitle": "👑 Premium pieces worth the investment",
                    "products": [p.dict() for p in luxury_products[:tier_config["products_per_section"]]]
                })

        # Section 6: Unlimited tier - Exclusive Finds (with gender preference)
        if tier == "unlimited":
            exclusive_query = f"{gender_prefix}limited edition exclusive rare vintage sneakers hoodie"
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
            # Try ONE last search with gender preference
            default_query = f"{gender_prefix}trendy teen fashion hoodie sneakers jeans"
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
        return count > 0


# Singleton instance
recommendation_service = RecommendationService()
