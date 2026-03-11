"""Product search service."""
import logging
import httpx
import random
import asyncio
import hashlib
import time
import re
from typing import List, Tuple, Dict, Any, Optional, Set
from ..schemas import Product, GeminiAnalysis
from ..config import settings

logger = logging.getLogger(__name__)

# Import the shared API tracker from recommendations
from .recommendations import api_tracker, SimpleCache


class ProductSearchService:
    """Service for searching products via APIs with intelligent filtering."""

    # Maximum query length for SerpAPI (keep it reasonable for Google Shopping)
    MAX_QUERY_LENGTH = 100

    # Color normalization mappings for better matching
    COLOR_ALIASES = {
        "white": ["white", "cream", "ivory", "off-white", "snow", "pearl", "eggshell"],
        "black": ["black", "ebony", "onyx", "charcoal", "jet"],
        "blue": ["blue", "navy", "cobalt", "azure", "indigo", "denim", "royal blue", "sky blue", "teal"],
        "red": ["red", "crimson", "scarlet", "burgundy", "maroon", "wine", "ruby", "cherry"],
        "green": ["green", "olive", "emerald", "sage", "forest", "mint", "hunter", "kelly"],
        "pink": ["pink", "blush", "rose", "coral", "salmon", "fuchsia", "magenta", "dusty rose"],
        "brown": ["brown", "tan", "camel", "beige", "khaki", "taupe", "chocolate", "cognac", "mocha"],
        "gray": ["gray", "grey", "silver", "charcoal", "slate", "ash", "heather"],
        "yellow": ["yellow", "gold", "mustard", "lemon", "amber", "honey"],
        "orange": ["orange", "rust", "tangerine", "peach", "terracotta", "copper"],
        "purple": ["purple", "lavender", "violet", "plum", "lilac", "mauve", "eggplant"],
    }

    # Item type keywords for filtering
    ITEM_TYPE_KEYWORDS = {
        "t-shirt": ["t-shirt", "tshirt", "tee", "t shirt"],
        "shirt": ["shirt", "blouse", "button-down", "button down", "oxford"],
        "hoodie": ["hoodie", "hooded", "sweatshirt", "pullover"],
        "jacket": ["jacket", "coat", "blazer", "bomber", "windbreaker", "parka", "outerwear"],
        "sweater": ["sweater", "jumper", "cardigan", "knit", "pullover"],
        "pants": ["pants", "trousers", "jeans", "chinos", "slacks", "joggers"],
        "shorts": ["shorts", "bermuda"],
        "dress": ["dress", "gown", "frock"],
        "skirt": ["skirt", "midi", "mini skirt", "maxi skirt"],
        "shoes": ["shoes", "sneakers", "boots", "loafers", "sandals", "heels", "flats", "trainers"],
        "bag": ["bag", "purse", "handbag", "tote", "backpack", "clutch", "crossbody"],
    }

    # Sleeve type keywords
    SLEEVE_KEYWORDS = {
        "long sleeve": ["long sleeve", "long-sleeve", "full sleeve"],
        "short sleeve": ["short sleeve", "short-sleeve", "half sleeve"],
        "sleeveless": ["sleeveless", "tank", "no sleeve"],
        "3/4 sleeve": ["3/4 sleeve", "three quarter", "elbow length"],
    }

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

    def _normalize_color(self, color: str) -> str:
        """Normalize color to a base color for matching."""
        color_lower = color.lower()
        for base_color, aliases in self.COLOR_ALIASES.items():
            for alias in aliases:
                if alias in color_lower:
                    return base_color
        return color_lower

    def _get_color_keywords(self, color: str) -> Set[str]:
        """Get all keywords that could match a color."""
        base = self._normalize_color(color)
        if base in self.COLOR_ALIASES:
            return set(self.COLOR_ALIASES[base])
        return {color.lower()}

    def _extract_item_category(self, item_type: str) -> Optional[str]:
        """Extract the base item category from a detailed item type."""
        item_lower = item_type.lower()
        for category, keywords in self.ITEM_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in item_lower:
                    return category
        return None

    def _extract_sleeve_type(self, text: str) -> Optional[str]:
        """Extract sleeve type from text."""
        text_lower = text.lower()
        for sleeve_type, keywords in self.SLEEVE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return sleeve_type
        return None

    def _calculate_real_similarity(
        self,
        product_title: str,
        product_description: str,
        analysis: GeminiAnalysis,
        is_exact_match: bool
    ) -> int:
        """
        Calculate REAL similarity based on attribute matching.
        Returns 0-100 score.
        """
        title_lower = product_title.lower()
        desc_lower = (product_description or "").lower()
        combined = f"{title_lower} {desc_lower}"

        score = 0
        max_score = 0

        # 1. Item type match (30 points max)
        max_score += 30
        expected_category = self._extract_item_category(analysis.item_type)
        if expected_category:
            for keyword in self.ITEM_TYPE_KEYWORDS.get(expected_category, []):
                if keyword in combined:
                    score += 30
                    break
        else:
            # Try direct match on item_type words
            item_words = analysis.item_type.lower().split()
            matches = sum(1 for word in item_words if word in combined and len(word) > 3)
            if matches > 0:
                score += min(30, matches * 10)

        # 2. Color match (25 points max)
        max_score += 25
        if analysis.colors:
            primary_color = analysis.colors[0]
            color_keywords = self._get_color_keywords(primary_color)
            for color_kw in color_keywords:
                if color_kw in combined:
                    score += 25
                    break
            else:
                # Check if ANY of the analysis colors match
                for color in analysis.colors:
                    color_keywords = self._get_color_keywords(color)
                    for color_kw in color_keywords:
                        if color_kw in combined:
                            score += 15  # Secondary color match
                            break
                    else:
                        continue
                    break

        # 3. Sleeve type match (15 points) - critical for shirts/tops
        max_score += 15
        expected_sleeve = self._extract_sleeve_type(analysis.item_type)
        if not expected_sleeve:
            expected_sleeve = self._extract_sleeve_type(analysis.detailed_description)

        if expected_sleeve:
            actual_sleeve = self._extract_sleeve_type(combined)
            if actual_sleeve == expected_sleeve:
                score += 15
            elif actual_sleeve and actual_sleeve != expected_sleeve:
                # Wrong sleeve type - major penalty
                score -= 20
        else:
            score += 10  # No sleeve expectation, neutral

        # 4. Material match (10 points)
        max_score += 10
        if analysis.material:
            material_words = analysis.material.lower().split()
            material_matches = sum(1 for word in material_words if word in combined and len(word) > 3)
            score += min(10, material_matches * 3)

        # 5. Style match (10 points)
        max_score += 10
        if analysis.style:
            style_words = analysis.style.lower().split()
            style_matches = sum(1 for word in style_words if word in combined and len(word) > 3)
            score += min(10, style_matches * 3)

        # 6. Brand match (10 points) - for exact match mode
        max_score += 10
        if analysis.brand and is_exact_match:
            if analysis.brand.lower() in combined:
                score += 10

        # Normalize to 0-100
        if max_score > 0:
            normalized = int((score / max_score) * 100)
        else:
            normalized = 50

        # Clamp to reasonable range
        normalized = max(0, min(100, normalized))

        # Add small random variation for natural feel
        variation = random.randint(-3, 3)
        normalized = max(0, min(100, normalized + variation))

        return normalized

    def _filter_product(
        self,
        product_title: str,
        analysis: GeminiAnalysis
    ) -> bool:
        """
        Filter out products that clearly don't match.
        Returns True if product should be KEPT, False if filtered out.
        """
        title_lower = product_title.lower()

        # Extract expected attributes
        expected_category = self._extract_item_category(analysis.item_type)
        expected_color = self._normalize_color(analysis.colors[0]) if analysis.colors else None
        expected_sleeve = self._extract_sleeve_type(analysis.item_type)
        if not expected_sleeve:
            expected_sleeve = self._extract_sleeve_type(analysis.detailed_description)

        # CRITICAL: Check for opposite colors (filter OUT wrong colors)
        if expected_color:
            opposite_colors = {
                "white": ["black", "dark"],
                "black": ["white", "light", "bright"],
                "blue": [],
                "red": [],
            }

            # If expected is white but product says black, filter it out
            if expected_color in opposite_colors:
                for wrong_color in opposite_colors[expected_color]:
                    # Only filter if the wrong color is prominent AND expected color is NOT present
                    color_keywords = self._get_color_keywords(expected_color)
                    expected_in_title = any(c in title_lower for c in color_keywords)

                    if wrong_color in title_lower and not expected_in_title:
                        logger.debug(f"Filtered out '{product_title}' - wrong color (expected {expected_color}, found {wrong_color})")
                        return False

        # CRITICAL: Check for sleeve type mismatch
        if expected_sleeve:
            actual_sleeve = self._extract_sleeve_type(title_lower)
            if actual_sleeve and actual_sleeve != expected_sleeve:
                # Different sleeve types - filter out
                logger.debug(f"Filtered out '{product_title}' - wrong sleeve (expected {expected_sleeve}, found {actual_sleeve})")
                return False

        # Check item category mismatch
        if expected_category:
            actual_category = self._extract_item_category(title_lower)
            if actual_category and actual_category != expected_category:
                # Different item type - filter out
                logger.debug(f"Filtered out '{product_title}' - wrong category (expected {expected_category}, found {actual_category})")
                return False

        return True

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

        IMPROVED: Now uses AI-optimized search_query and filters mismatched results.

        Strategy based on subscription tier:
        - Free: Basic exact matches + limited alternatives (15 max)
        - Basic: More results + budget alternatives (25 max)
        - Pro: Luxury + trending searches + enhanced results (40 max)
        - Unlimited: All features + maximum results (60 max)

        Gender parameter filters results: 'male', 'female', or 'either'.
        Search mode: 'exact' prioritizes finding the same item, 'alternatives' focuses on similar/cheaper options.
        """
        if not settings.SERPAPI_API_KEY:
            logger.warning("No SERPAPI_API_KEY found. Returning empty results.")
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

        # Log what we're searching for
        logger.info(f"Searching for: item_type='{analysis.item_type}', colors={analysis.colors}, search_query='{analysis.search_query}'")

        if search_mode == "exact":
            # EXACT MODE: Use AI-optimized query first
            exact_query = self._build_exact_query(analysis, gender_prefix)
            logger.info(f"Exact search query: '{exact_query}'")

            exact_products = await self._search_serpapi(exact_query, analysis, is_exact_match=True, num_results=tier_limits["exact_limit"] + 20)
            all_products.extend(exact_products)
            existing_ids = {p.id for p in all_products}

            # Fallback if filtering removed too many results
            if len(all_products) < 5:
                logger.info("Few results after filtering, trying fallback query...")
                style_query = self._build_style_query(analysis, gender_prefix)
                style_products = await self._search_serpapi(style_query, analysis, is_exact_match=True, num_results=20)
                for product in style_products:
                    if product.id not in existing_ids:
                        all_products.append(product)
                        existing_ids.add(product.id)

        else:
            # ALTERNATIVES MODE: AI-optimized query is critical here
            alt_query = self._build_alternative_query(analysis, gender_prefix)
            logger.info(f"Alternative search query: '{alt_query}'")

            alt_products = await self._search_serpapi(alt_query, analysis, is_exact_match=False, num_results=tier_limits["alt_limit"] + 20)

            for product in alt_products:
                if product.id not in existing_ids:
                    all_products.append(product)
                    existing_ids.add(product.id)

            # If too few results, try a more specific query with key features
            if len(all_products) < 8:
                logger.info("Few results, trying feature-focused fallback...")
                feature_query = self._build_feature_query(analysis, gender_prefix)
                feature_products = await self._search_serpapi(feature_query, analysis, is_exact_match=False, num_results=20)
                for product in feature_products:
                    if product.id not in existing_ids:
                        all_products.append(product)
                        existing_ids.add(product.id)

        # Sort results based on search mode
        if search_mode == "exact":
            all_products.sort(key=lambda p: p.similarity_percentage, reverse=True)
        else:
            all_products.sort(key=lambda p: p.price if p.price > 0 else float('inf'))

        # Limit to tier maximum
        max_results = tier_limits["max_total"]
        if len(all_products) > max_results:
            all_products = all_products[:max_results]

        return all_products

    def _build_exact_query(self, analysis: GeminiAnalysis, gender_prefix: str) -> str:
        """Build search query for exact brand/item matches."""
        # PRIORITY 1: Use AI-optimized search_query if available
        if analysis.search_query and len(analysis.search_query.strip()) > 5:
            query = analysis.search_query.strip()
            if gender_prefix:
                query = f"{gender_prefix.strip()} {query}"
            if analysis.brand:
                query = f"{analysis.brand} {query}"
            return self._truncate_query(query)

        # FALLBACK: Build query from components
        parts = []

        if gender_prefix:
            parts.append(gender_prefix.strip())

        # Brand is critical for exact match
        if analysis.brand:
            parts.append(analysis.brand)

        # Primary color with shade
        if analysis.colors:
            parts.append(analysis.colors[0])

        # Full item type (keeps descriptors like "long sleeve")
        parts.append(analysis.item_type)

        # Add key distinguishing features
        if analysis.material:
            # Extract key material word
            material_words = analysis.material.split()[:2]
            parts.extend(material_words)

        return " ".join(parts)

    def _build_alternative_query(self, analysis: GeminiAnalysis, gender_prefix: str) -> str:
        """Build search query for alternative/similar items (no brand, focus on style)."""
        # PRIORITY 1: Use AI-optimized search_query if available
        if analysis.search_query and len(analysis.search_query.strip()) > 5:
            query = analysis.search_query.strip()
            if gender_prefix:
                query = f"{gender_prefix.strip()} {query}"
            return self._truncate_query(query)

        # FALLBACK: Build query from components
        parts = []

        if gender_prefix:
            parts.append(gender_prefix.strip())

        # Primary color - CRITICAL for matching
        if analysis.colors:
            parts.append(analysis.colors[0])

        # Full item type (includes descriptors)
        parts.append(analysis.item_type)

        # Material adds specificity
        if analysis.material:
            material_key = analysis.material.split()[0]
            parts.append(material_key)

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
            material_key = analysis.material.split()[0]
            parts.append(material_key)

        return " ".join(parts)

    def _build_feature_query(self, analysis: GeminiAnalysis, gender_prefix: str) -> str:
        """Build search query focusing on key features (fallback for alternatives)."""
        parts = []

        if gender_prefix:
            parts.append(gender_prefix.strip())

        # Primary color - ALWAYS include
        if analysis.colors:
            parts.append(analysis.colors[0])

        # Item type - ALWAYS include
        parts.append(analysis.item_type)

        # Add most important key features (first 2)
        if analysis.key_features and len(analysis.key_features) > 0:
            # Take first 2 features, clean them up
            for feature in analysis.key_features[:2]:
                # Extract meaningful words (skip generic terms)
                feature_words = [w for w in feature.lower().split() if len(w) > 3 and w not in ["type", "style", "with"]]
                if feature_words:
                    parts.append(feature_words[0])

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
                return cached_result

            # Check daily API limit
            if not api_tracker.can_make_call():
                logger.warning(f"Daily API limit reached. Skipping search.")
                return []

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

            # Handle rate limiting
            if response.status_code == 429:
                logger.warning("SerpApi rate limit hit (429). Waiting and retrying...")
                await asyncio.sleep(2)  # Wait 2 seconds before retry
                response = await self.client.get("https://serpapi.com/search", params=params)
                if response.status_code == 429:
                    logger.error("SerpApi rate limit still in effect. Skipping this search.")
                    return []

            response.raise_for_status()
            data = response.json()

            if "error" in data:
                logger.error(f"SerpApi returned error: {data.get('error', 'Unknown')}")
                return []

            shopping_results = data.get("shopping_results", [])
            logger.info(f"SERP returned {len(shopping_results)} results for query: '{query}'")

            products = []
            filtered_count = 0

            for i, item in enumerate(shopping_results):
                title = item.get("title", "")
                snippet = item.get("snippet", "")

                # CRITICAL: Filter out products that don't match
                if not self._filter_product(title, analysis):
                    filtered_count += 1
                    continue

                # Get the best available link
                # Priority: product_link (direct merchant) > link (Google Shopping page)
                # Both should work - Google Shopping links redirect to merchant
                link = item.get("product_link") or item.get("link") or item.get("source_link")

                # If no link, try to construct a search URL
                if not link:
                    source = item.get("source", "")
                    if title:
                        # Create a Google Shopping search link as fallback
                        import urllib.parse
                        search_query_url = urllib.parse.quote(f"{title} {source}")
                        link = f"https://www.google.com/search?q={search_query_url}&tbm=shop"
                    else:
                        continue

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

                # Calculate REAL similarity based on attribute matching
                similarity = self._calculate_real_similarity(
                    title,
                    snippet,
                    analysis,
                    is_exact_match
                )

                # Skip products with very low similarity (likely wrong results)
                if similarity < 40:
                    filtered_count += 1
                    logger.debug(f"Filtered low-similarity product: '{title}' (score: {similarity})")
                    continue

                products.append(Product(
                    id=item.get("product_id", f"serp_{i}_{random.randint(1000, 9999)}"),
                    title=title or "Unknown Product",
                    description=snippet or analysis.detailed_description[:100],
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

            logger.info(f"After filtering: {len(products)} products kept, {filtered_count} filtered out")

            # Cache the results
            self._search_cache.set(cache_key, products)

            return products

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("SerpApi rate limit exceeded (429). Caching empty result.")
            else:
                logger.error(f"SerpApi HTTP error {e.response.status_code}")
            # Cache empty result to prevent repeated failed calls
            self._search_cache.set(cache_key, [])
            return []
        except Exception as e:
            logger.error(f"Exception searching products via SerpApi: {e}")
            # Cache empty result to prevent repeated failed calls
            self._search_cache.set(cache_key, [])
            return []

    async def _get_mock_products(self, analysis: GeminiAnalysis, search_query: str) -> List[Product]:
        """Deprecated mock method."""
        return []


# Singleton instance
product_search_service = ProductSearchService()
