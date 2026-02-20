"""Product search service."""
import httpx
import random
import asyncio
import hashlib
import time
from typing import List, Tuple, Dict, Any, Optional
from ..schemas import Product, GeminiAnalysis
from ..config import settings

# Import the shared API tracker from recommendations
from .recommendations import api_tracker, SimpleCache


class ProductSearchService:
    """Service for searching products via APIs."""

    # Maximum query length for SerpAPI (keep it reasonable for Google Shopping)
    MAX_QUERY_LENGTH = 100

    def __init__(self):
        """Initialize product search service."""
        self.client = httpx.AsyncClient(timeout=30.0)
        self._last_request_time = 0
        self._min_request_interval = 1.0  # 1 second between requests to avoid rate limits
        # Cache for search results (2 hour TTL - aggressive caching)
        self._search_cache = SimpleCache(ttl_seconds=7200)

    def _truncate_query(self, query: str) -> str:
        """Truncate and clean a search query to a reasonable length."""
        # Remove extra whitespace
        query = " ".join(query.split())

        # If query is already short enough, return it
        if len(query) <= self.MAX_QUERY_LENGTH:
            return query

        # Truncate at word boundary
        truncated = query[:self.MAX_QUERY_LENGTH]
        last_space = truncated.rfind(" ")
        if last_space > 50:  # Keep at least 50 chars
            truncated = truncated[:last_space]

        return truncated.strip()

    def _clean_search_term(self, term: str) -> str:
        """Clean a search term to be concise and effective."""
        # Remove parenthetical content like "(Pantone 15-4305 TPX)"
        import re
        term = re.sub(r'\([^)]*\)', '', term)

        # Remove common filler words and overly descriptive phrases
        term = re.sub(r'\b(likely|possibly|probably|approximately|around|about)\b', '', term, flags=re.IGNORECASE)

        # Clean up extra whitespace
        term = " ".join(term.split())

        return self._truncate_query(term)

    def _get_tier_limits(self, tier: str) -> dict:
        """Get search limits and features based on subscription tier."""
        limits = {
            "free": {
                "exact_limit": 10,
                "alt_limit": 15,
                "max_total": 15,
                "include_luxury": False,
                "include_trending": False,
                "include_budget": False,
            },
            "basic": {
                "exact_limit": 15,
                "alt_limit": 20,
                "max_total": 25,
                "include_luxury": False,
                "include_trending": False,
                "include_budget": True,
            },
            "pro": {
                "exact_limit": 25,
                "alt_limit": 30,
                "max_total": 40,
                "include_luxury": True,
                "include_trending": True,
                "include_budget": True,
            },
            "unlimited": {
                "exact_limit": 35,
                "alt_limit": 40,
                "max_total": 60,
                "include_luxury": True,
                "include_trending": True,
                "include_budget": True,
            }
        }
        return limits.get(tier, limits["free"])

    async def search_products(self, analysis: GeminiAnalysis, gender: str = "either", tier: str = "free", search_mode: str = "alternatives") -> List[Product]:
        """
        Search for products based on Gemini analysis using SerpApi (Google Shopping).

        Strategy based on subscription tier:
        - Free: Basic exact matches + limited alternatives (15 max)
        - Basic: More results + budget alternatives (25 max)
        - Pro: Luxury + trending searches + enhanced results (40 max)
        - Unlimited: All features + maximum results (60 max)

        Gender parameter filters results: 'male', 'female', or 'either'.
        Search mode: 'exact' prioritizes finding the same item, 'alternatives' focuses on similar/cheaper options.
        """
        if not settings.SERPAPI_API_KEY:
            print("Warning: No SERPAPI_API_KEY found. Returning empty results.")
            return []

        all_products = []
        tier_limits = self._get_tier_limits(tier)

        # Gender prefix for queries
        gender_prefix = ""
        if gender == "male":
            gender_prefix = "men's "
        elif gender == "female":
            gender_prefix = "women's "

        existing_ids = set()

        print(f"DEBUG: Search mode is '{search_mode}'")

        # ===========================================
        # API CONSERVATION: Limit to 2 queries max per search!
        # ===========================================

        if search_mode == "exact":
            # EXACT MODE: Just 1-2 API calls total
            # Query 1: Full brand + item search (most specific)
            exact_query = self._build_exact_query(analysis, gender_prefix)
            print(f"DEBUG [EXACT MODE]: Primary search: '{exact_query}'")
            exact_products = await self._search_serpapi(exact_query, analysis, is_exact_match=True, num_results=tier_limits["exact_limit"] + 15)
            all_products.extend(exact_products)
            existing_ids = {p.id for p in all_products}
            print(f"DEBUG [EXACT MODE]: Found {len(exact_products)} exact match products")

            # Only do a second query if we got few results
            if len(all_products) < 5:
                style_query = self._build_style_query(analysis, gender_prefix)
                print(f"DEBUG [EXACT MODE]: Fallback style search: '{style_query}'")
                style_products = await self._search_serpapi(style_query, analysis, is_exact_match=True, num_results=15)
                for product in style_products:
                    if product.id not in existing_ids:
                        all_products.append(product)
                        existing_ids.add(product.id)

        else:
            # ALTERNATIVES MODE: Just 2 API calls total
            # Query 1: Exact match for reference (smaller result set)
            if analysis.brand:
                exact_query = self._build_exact_query(analysis, gender_prefix)
                print(f"DEBUG [ALT MODE]: Reference search: '{exact_query}'")
                exact_products = await self._search_serpapi(exact_query, analysis, is_exact_match=True, num_results=5)
                all_products.extend(exact_products)
                existing_ids = {p.id for p in all_products}

            # Query 2: Alternatives with combined keywords (one smart query)
            alt_query = self._build_alternative_query(analysis, gender_prefix)
            # Add budget/affordable keywords to find cheaper options
            if tier_limits["include_budget"]:
                alt_query += " affordable"
            print(f"DEBUG [ALT MODE]: Alternatives search: '{alt_query}'")
            alt_products = await self._search_serpapi(alt_query, analysis, is_exact_match=False, num_results=tier_limits["alt_limit"] + 10)

            for product in alt_products:
                if product.id not in existing_ids:
                    all_products.append(product)
                    existing_ids.add(product.id)
            print(f"DEBUG [ALT MODE]: Found {len(alt_products)} alternative products")

        # NOTE: Tier-based luxury/trending searches DISABLED to conserve API calls
        # Users still get differentiated by result limits, not by extra searches

        # STEP 4: Sort results based on search mode
        if search_mode == "exact":
            # Exact mode: Sort by similarity (highest first) to show best matches
            all_products.sort(key=lambda p: p.similarity_percentage, reverse=True)
        else:
            # Alternatives mode: Sort by price (cheapest first) for budget-conscious shopping
            all_products.sort(key=lambda p: p.price if p.price > 0 else float('inf'))

        # STEP 5: Limit to tier maximum
        max_results = tier_limits["max_total"]
        if len(all_products) > max_results:
            all_products = all_products[:max_results]

        print(f"DEBUG: Returning {len(all_products)} products (tier={tier}, mode={search_mode}, max={max_results})")
        return all_products

    def _build_exact_query(self, analysis: GeminiAnalysis, gender_prefix: str) -> str:
        """Build search query for exact brand/item matches."""
        parts = []

        if gender_prefix:
            parts.append(gender_prefix.strip())

        # Brand is critical for exact match
        if analysis.brand:
            parts.append(analysis.brand)

        # Primary color
        if analysis.colors:
            parts.append(analysis.colors[0])

        # Item type
        parts.append(analysis.item_type)

        return " ".join(parts)

    def _build_alternative_query(self, analysis: GeminiAnalysis, gender_prefix: str) -> str:
        """Build search query for alternative/similar items (no brand, focus on style)."""
        parts = []

        if gender_prefix:
            parts.append(gender_prefix.strip())

        # Primary color
        if analysis.colors:
            parts.append(analysis.colors[0])

        # Item type
        parts.append(analysis.item_type)

        # Style descriptor
        if analysis.style:
            parts.append(analysis.style)

        # Add "affordable" or "budget" to find cheaper options
        parts.append("affordable")

        return " ".join(parts)

    def _build_budget_query(self, analysis: GeminiAnalysis, gender_prefix: str) -> str:
        """Build search query for budget-friendly alternatives."""
        parts = []

        if gender_prefix:
            parts.append(gender_prefix.strip())

        # Primary color
        if analysis.colors:
            parts.append(analysis.colors[0])

        # Item type
        parts.append(analysis.item_type)

        # Add budget keywords
        parts.append("cheap affordable under $50")

        return " ".join(parts)

    def _build_luxury_query(self, analysis: GeminiAnalysis, gender_prefix: str) -> str:
        """Build search query for luxury/designer alternatives (Pro/Unlimited feature)."""
        parts = []

        if gender_prefix:
            parts.append(gender_prefix.strip())

        # Primary color
        if analysis.colors:
            parts.append(analysis.colors[0])

        # Item type
        parts.append(analysis.item_type)

        # Style descriptor
        if analysis.style:
            parts.append(analysis.style)

        # Add luxury keywords
        parts.append("designer luxury premium")

        return " ".join(parts)

    def _build_trending_query(self, analysis: GeminiAnalysis, gender_prefix: str) -> str:
        """Build search query for trending/popular items (premium feature)."""
        parts = []

        if gender_prefix:
            parts.append(gender_prefix.strip())

        # Primary color
        if analysis.colors:
            parts.append(analysis.colors[0])

        # Item type
        parts.append(analysis.item_type)

        # Add trending keywords
        parts.append("trending 2026 popular")

        return " ".join(parts)

    def _build_style_query(self, analysis: GeminiAnalysis, gender_prefix: str) -> str:
        """Build search query focusing on style characteristics (for exact match fallback)."""
        parts = []

        if gender_prefix:
            parts.append(gender_prefix.strip())

        # Style descriptor
        if analysis.style:
            parts.append(analysis.style)

        # Primary color
        if analysis.colors:
            parts.append(analysis.colors[0])

        # Item type
        parts.append(analysis.item_type)

        # Material if known
        if analysis.material:
            parts.append(analysis.material)

        return " ".join(parts)

    async def _search_serpapi(
        self,
        query: str,
        analysis: GeminiAnalysis,
        is_exact_match: bool,
        num_results: int = 20
    ) -> List[Product]:
        """Execute a SerpApi search and parse results with caching."""
        try:
            # Truncate query to reasonable length
            query = self._truncate_query(query)

            # Check cache first
            cache_key = hashlib.md5(f"search:{query}:{num_results}:{is_exact_match}".encode()).hexdigest()
            cached_result = self._search_cache.get(cache_key)
            if cached_result is not None:
                print(f"DEBUG [Search Cache HIT]: '{query[:40]}...' - returning {len(cached_result)} cached products")
                return cached_result

            # Check daily API limit
            if not api_tracker.can_make_call():
                print(f"WARNING [API Limit]: Daily limit reached. Skipping search for '{query[:30]}'")
                return []

            print(f"DEBUG: Final search query ({len(query)} chars): '{query}'")

            # Rate limiting - wait if needed (1 second minimum)
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
                "num": num_results
                # Note: We sort results by price in Python after fetching
            }

            response = await self.client.get("https://serpapi.com/search", params=params)
            print(f"DEBUG: SerpApi response status: {response.status_code}")

            # Handle rate limiting
            if response.status_code == 429:
                print("WARNING: SerpApi rate limit hit (429). Waiting and retrying...")
                await asyncio.sleep(2)  # Wait 2 seconds before retry
                response = await self.client.get("https://serpapi.com/search", params=params)
                if response.status_code == 429:
                    print("ERROR: SerpApi rate limit still in effect. Skipping this search.")
                    return []

            response.raise_for_status()
            data = response.json()

            if "error" in data:
                print(f"ERROR: SerpApi returned error: {data['error']}")
                return []

            shopping_results = data.get("shopping_results", [])
            print(f"DEBUG: SerpApi returned {len(shopping_results)} results for query")

            if shopping_results:
                print(f"DEBUG: First item keys: {list(shopping_results[0].keys())}")

            products = []
            for i, item in enumerate(shopping_results):
                # Debug: print first few items to see structure
                if i < 2:
                    print(f"DEBUG: Item {i} data: {item}")

                # Get the best available link
                # Priority: product_link (direct merchant) > link (Google Shopping page)
                # Both should work - Google Shopping links redirect to merchant
                link = item.get("product_link") or item.get("link") or item.get("source_link")

                # If no link, try to construct a search URL
                if not link:
                    title = item.get("title", "")
                    source = item.get("source", "")
                    if title:
                        # Create a Google Shopping search link as fallback
                        import urllib.parse
                        search_query = urllib.parse.quote(f"{title} {source}")
                        link = f"https://www.google.com/search?q={search_query}&tbm=shop"
                        print(f"DEBUG: Item {i} - created search fallback link")
                    else:
                        print(f"DEBUG: Item {i} has no link and no title, skipping")
                        continue

                if i == 0:
                    print(f"DEBUG: Using link type: {'product_link' if item.get('product_link') else 'link/fallback'}")
                    print(f"DEBUG: Link value: {link[:100]}...")

                # Extract price - try extracted_price first (numeric), then parse price string
                price = item.get("extracted_price", 0)
                if not price or price == 0:
                    price_str = str(item.get("price", "0")).replace("$", "").replace(",", "").strip()
                    try:
                        price = float(price_str) if price_str else 0.0
                    except ValueError:
                        price = 0.0

                # Don't skip items with 0 price - just set a default
                if price <= 0:
                    price = 0.01  # Set minimal price instead of skipping

                # Extract original price if available
                orig_price_str = item.get("extracted_old_price")
                original_price = float(orig_price_str) if orig_price_str else None

                # Calculate similarity percentage
                # Exact matches (same brand): 92-99%
                # Alternatives: 75-89%
                if is_exact_match:
                    similarity = random.randint(92, 99)
                else:
                    similarity = random.randint(75, 89)

                # Check if product title contains the brand for higher similarity
                title = item.get("title", "").lower()
                if analysis.brand and analysis.brand.lower() in title:
                    similarity = max(similarity, 94)

                products.append(Product(
                    id=item.get("product_id", f"serp_{i}_{random.randint(1000, 9999)}"),
                    title=item.get("title", "Unknown Product"),
                    description=item.get("snippet") or analysis.detailed_description[:100],
                    price=price,
                    original_price=original_price,
                    currency="USD",
                    image_url=item.get("thumbnail", "https://via.placeholder.com/300"),
                    merchant=item.get("source", "Unknown Seller"),
                    affiliate_link=link,
                    similarity_percentage=similarity,
                    brand=item.get("source", "Unknown"),
                    category=analysis.item_type
                ))

            # Cache the results
            self._search_cache.set(cache_key, products)
            print(f"DEBUG [Search Cache SET]: '{query[:40]}...' - cached {len(products)} products")

            return products

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                print(f"ERROR: SerpApi rate limit exceeded (429). Caching empty result.")
            else:
                print(f"ERROR: SerpApi HTTP error {e.response.status_code}: {e}")
            # Cache empty result to prevent repeated failed calls
            self._search_cache.set(cache_key, [])
            return []
        except Exception as e:
            import traceback
            print(f"ERROR: Exception searching products via SerpApi: {e}")
            traceback.print_exc()
            # Cache empty result to prevent repeated failed calls
            self._search_cache.set(cache_key, [])
            return []

    async def _get_mock_products(self, analysis: GeminiAnalysis, search_query: str) -> List[Product]:
        """Deprecated mock method."""
        return []


# Singleton instance
product_search_service = ProductSearchService()
