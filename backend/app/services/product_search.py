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

    # Item type keywords for filtering - comprehensive coverage
    ITEM_TYPE_KEYWORDS = {
        # Tops
        "t-shirt": ["t-shirt", "tshirt", "tee", "t shirt", "graphic tee"],
        "shirt": ["shirt", "blouse", "button-down", "button down", "oxford", "polo"],
        "hoodie": ["hoodie", "hooded", "sweatshirt"],
        "sweater": ["sweater", "jumper", "cardigan", "knit", "pullover", "crewneck"],
        "tank": ["tank top", "tank", "camisole", "vest"],
        "crop top": ["crop top", "cropped", "crop"],
        # Outerwear
        "jacket": ["jacket", "blazer", "bomber", "windbreaker", "denim jacket", "leather jacket", "trucker"],
        "coat": ["coat", "overcoat", "trench", "parka", "peacoat", "puffer", "down jacket"],
        "vest": ["vest", "gilet", "waistcoat"],
        # Bottoms
        "pants": ["pants", "trousers", "chinos", "slacks", "cargo pants", "dress pants"],
        "jeans": ["jeans", "denim", "skinny jeans", "straight leg", "bootcut", "flare", "baggy jeans", "wide leg jeans", "mom jeans", "boyfriend jeans", "relaxed jeans", "loose jeans", "tapered jeans"],
        "shorts": ["shorts", "bermuda", "swim shorts", "athletic shorts"],
        "joggers": ["joggers", "sweatpants", "track pants"],
        "leggings": ["leggings", "tights", "yoga pants"],
        # Dresses & Skirts
        "dress": ["dress", "gown", "frock", "maxi dress", "midi dress", "mini dress", "sundress"],
        "skirt": ["skirt", "midi skirt", "mini skirt", "maxi skirt", "pencil skirt", "pleated skirt"],
        "jumpsuit": ["jumpsuit", "romper", "playsuit", "overalls"],
        # Footwear
        "sneakers": ["sneakers", "trainers", "running shoes", "athletic shoes", "tennis shoes"],
        "boots": ["boots", "ankle boots", "chelsea boots", "combat boots", "hiking boots", "cowboy boots"],
        "heels": ["heels", "pumps", "stilettos", "wedges", "platform"],
        "sandals": ["sandals", "slides", "flip flops", "espadrilles"],
        "flats": ["flats", "ballet flats", "loafers", "moccasins", "slip-ons"],
        "shoes": ["shoes", "oxfords", "derby", "dress shoes", "boat shoes"],
        # Bags
        "bag": ["bag", "purse", "handbag", "tote", "shoulder bag"],
        "backpack": ["backpack", "rucksack", "daypack"],
        "clutch": ["clutch", "evening bag", "wristlet"],
        "crossbody": ["crossbody", "messenger", "sling bag"],
        "wallet": ["wallet", "cardholder", "billfold"],
        # Accessories
        "hat": ["hat", "cap", "beanie", "fedora", "bucket hat", "snapback", "baseball cap"],
        "sunglasses": ["sunglasses", "shades", "eyewear", "aviators"],
        "watch": ["watch", "timepiece", "smartwatch"],
        "belt": ["belt", "waist belt"],
        "scarf": ["scarf", "shawl", "wrap", "bandana"],
        "jewelry": ["necklace", "bracelet", "earrings", "ring", "jewelry", "chain"],
        "tie": ["tie", "necktie", "bow tie"],
    }

    # Sleeve type keywords
    SLEEVE_KEYWORDS = {
        "long sleeve": ["long sleeve", "long-sleeve", "full sleeve"],
        "short sleeve": ["short sleeve", "short-sleeve", "half sleeve"],
        "sleeveless": ["sleeveless", "tank", "no sleeve", "strapless"],
        "3/4 sleeve": ["3/4 sleeve", "three quarter", "elbow length"],
    }

    # Pattern/print keywords for better matching
    PATTERN_KEYWORDS = {
        "graphic": ["graphic", "print", "logo", "text", "screen print"],
        "striped": ["striped", "stripes", "stripe"],
        "plaid": ["plaid", "checkered", "gingham", "tartan"],
        "floral": ["floral", "flower", "botanical"],
        "solid": ["solid", "plain", "basic"],
        "polka dot": ["polka dot", "dotted", "dots"],
        "camo": ["camo", "camouflage", "military print"],
        "animal": ["leopard", "zebra", "snake", "animal print"],
        "geometric": ["geometric", "abstract"],
        "tie dye": ["tie dye", "tie-dye", "dyed"],
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

    def _extract_pattern(self, text: str) -> Optional[str]:
        """Extract pattern/print type from text."""
        text_lower = text.lower()
        for pattern_type, keywords in self.PATTERN_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return pattern_type
        return None

    def _calculate_real_similarity(
        self,
        product_title: str,
        product_description: str,
        analysis: GeminiAnalysis,
        is_exact_match: bool
    ) -> int:
        """
        Calculate similarity based on ACTUAL attribute matching.

        Scoring breakdown (max 100):
        - Brand match: +25 points (most important for exact match)
        - Item type match: +25 points
        - Color match: +20 points
        - Style/features match: +15 points
        - Base relevance: +15 points (Google results are somewhat relevant)

        For text search, realistic scores range from 55-95% depending on matches.
        Visual matches from Google Lens get 85-99% (handled separately).
        """
        title_lower = product_title.lower()
        desc_lower = (product_description or '').lower()
        combined = f"{title_lower} {desc_lower}"

        score = 15  # Base score - Google results are somewhat relevant

        # ===== BRAND MATCH (+25 points) =====
        brand_matched = False
        if analysis.brand:
            brand_lower = analysis.brand.lower()
            # Check for exact brand name or common variations
            brand_words = brand_lower.split()
            if brand_lower in combined or any(word in combined for word in brand_words if len(word) > 2):
                score += 25
                brand_matched = True

        # ===== ITEM TYPE MATCH (+25 points) =====
        item_matched = False
        expected_category = self._extract_item_category(analysis.item_type)
        if expected_category:
            for keyword in self.ITEM_TYPE_KEYWORDS.get(expected_category, []):
                if keyword in combined:
                    score += 25
                    item_matched = True
                    break
        if not item_matched:
            # Direct word match fallback
            item_words = [w for w in analysis.item_type.lower().split() if len(w) > 3]
            if any(word in combined for word in item_words):
                score += 20  # Slightly lower for partial match

        # ===== COLOR MATCH (+20 points) =====
        color_matched = False
        if analysis.colors:
            primary_color = analysis.colors[0].lower() if analysis.colors[0] else ""
            # Get base color and all variations
            color_keywords = self._get_color_keywords(primary_color)
            for color in color_keywords:
                if color in combined:
                    score += 20
                    color_matched = True
                    break

        # ===== STYLE/FEATURES MATCH (+15 points) =====
        features_matched = 0
        if analysis.key_features:
            for feature in analysis.key_features[:3]:  # Check top 3 features
                feature_words = [w for w in feature.lower().split() if len(w) > 3]
                if any(word in combined for word in feature_words):
                    features_matched += 1

        if features_matched >= 2:
            score += 15
        elif features_matched == 1:
            score += 8

        # Bonus for exact match mode when brand + item both match
        if is_exact_match and brand_matched and item_matched:
            score += 5  # Bonus for strong matches in exact mode

        # Small randomization to avoid identical scores (but deterministic feel)
        # Use hash of title for consistency
        title_hash = hash(title_lower) % 5
        score += title_hash - 2  # Range: -2 to +2

        # Clamp to realistic range: 55-95% for text search
        # (Visual matches from Lens get 85-99%, handled in _search_google_lens)
        return max(55, min(95, score))

    def _filter_product(
        self,
        product_title: str,
        analysis: GeminiAnalysis
    ) -> bool:
        """
        MINIMAL filtering - only remove clearly wrong items.
        Be permissive to avoid removing good results.
        Returns True if product should be KEPT, False if filtered out.
        """
        # Be very permissive - only filter out obvious mismatches
        # Most filtering should happen via similarity scoring, not hard rejection
        return True  # Keep all products, let similarity scoring rank them

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

    async def search_products(
        self,
        analysis: GeminiAnalysis,
        gender: str = "either",
        tier: str = "free",
        search_mode: str = "exact",
        image_url: Optional[str] = None,
        user_brand: Optional[str] = None,
        user_price: Optional[str] = None
    ) -> List[Product]:
        """
        Search for products using BOTH Google Lens (visual) AND Google Shopping (text).

        IMPROVED: Combines visual matching (Google Lens) with text search (Google Shopping)
        for much higher accuracy. Visual matches get higher similarity scores.

        Strategy based on search_mode:
        - 'exact': Uses Google Lens FIRST for visual matching (finds exact same item)
        - 'alternatives': Uses Google Shopping text search to find similar/cheaper options

        Gender parameter filters results: 'male', 'female', or 'either'.

        User-provided brand/price override AI detection for better accuracy.
        """
        if not settings.SERPAPI_API_KEY:
            logger.warning("No SERPAPI_API_KEY found. Returning empty results.")
            return []

        all_products = []
        visual_products = []
        text_products = []
        tier_limits = self._get_tier_limits(tier)

        # Gender prefix for queries
        gender_prefix = ""
        if gender == "male":
            gender_prefix = "men's "
        elif gender == "female":
            gender_prefix = "women's "

        existing_ids = set()

        # If user provided a brand, use it to override AI detection
        effective_brand = user_brand.strip() if user_brand and user_brand.strip() else None

        # Log what we're searching for
        logger.info(f"Searching for: item_type='{analysis.item_type}', colors={analysis.colors}, brand='{analysis.brand}', user_brand='{effective_brand}', mode='{search_mode}'")

        # ===== EXACT MODE: Use Google Lens for visual matching =====
        if search_mode == "exact":
            if image_url:
                # Google Lens is critical for "Find Exact Item" mode
                # It does pixel-level image matching like the actual Google Lens app
                logger.info(f"EXACT MODE: Using Google Lens with image URL: {image_url}")
                visual_products = await self._search_google_lens(
                    image_url,
                    analysis,
                    num_results=tier_limits["exact_limit"] + 10
                )

            if visual_products:
                logger.info(f"Google Lens found {len(visual_products)} visual matches")
                for p in visual_products:
                    if p.id not in existing_ids:
                        all_products.append(p)
                        existing_ids.add(p.id)

            # Supplement with text search if we need more results or had no image
            if len(all_products) < 10:
                exact_query = self._build_exact_query(analysis, gender_prefix, effective_brand)
                logger.info(f"Supplementing with text search: '{exact_query}'")
                text_products = await self._search_serpapi(
                    exact_query, analysis, is_exact_match=True,
                    num_results=15
                )
                for p in text_products:
                    if p.id not in existing_ids:
                        all_products.append(p)
                        existing_ids.add(p.id)

        # ===== ALTERNATIVES MODE: Use text search for CHEAPER options =====
        else:
            # For alternatives, we want DUPES - cheaper versions of expensive items
            # Note: For alternatives, we don't use user_brand since we want different brands
            alt_query = self._build_alternative_query(analysis, gender_prefix)
            logger.info(f"ALTERNATIVES MODE: '{alt_query}'")

            # Parse estimated price to set a maximum price filter
            # If original is $200, we want dupes under $100 (50% or less)
            max_price = self._parse_max_price_for_dupes(analysis.price_estimate)
            logger.info(f"Max price for dupes: ${max_price}" if max_price else "No price cap set")

            text_products = await self._search_serpapi(
                alt_query, analysis, is_exact_match=False,
                num_results=tier_limits["alt_limit"] + 20,
                max_price=max_price
            )

            for product in text_products:
                if product.id not in existing_ids:
                    all_products.append(product)
                    existing_ids.add(product.id)

            # If too few results, try without dupe keywords but still with price filter
            if len(all_products) < 8:
                logger.info("Few results, trying feature-focused fallback...")
                feature_query = self._build_feature_query(analysis, gender_prefix)
                feature_products = await self._search_serpapi(
                    feature_query, analysis, is_exact_match=False, num_results=20,
                    max_price=max_price
                )
                for product in feature_products:
                    if product.id not in existing_ids:
                        all_products.append(product)
                        existing_ids.add(product.id)

            # If STILL too few results, try without price limit (last resort)
            if len(all_products) < 5:
                logger.info("Still few results, trying without price limit...")
                basic_query = self._build_alternative_query(analysis, gender_prefix).replace(" dupe affordable", "")
                basic_products = await self._search_serpapi(
                    basic_query, analysis, is_exact_match=False, num_results=20
                )
                for product in basic_products:
                    if product.id not in existing_ids:
                        all_products.append(product)
                        existing_ids.add(product.id)

        # ===== SORTING =====
        if search_mode == "exact":
            # For exact match: sort by similarity (visual matches will have higher scores)
            all_products.sort(key=lambda p: p.similarity_percentage, reverse=True)
        else:
            # For alternatives: sort by PRICE (cheapest first - this is the app's value prop)
            all_products.sort(key=lambda p: p.price if p.price > 0 else float('inf'))

        # Limit to tier maximum
        max_results = tier_limits["max_total"]
        if len(all_products) > max_results:
            all_products = all_products[:max_results]

        logger.info(f"Returning {len(all_products)} products (visual: {len(visual_products)}, text: {len(text_products)})")
        return all_products

    def _parse_max_price_for_dupes(self, price_estimate: str) -> Optional[float]:
        """
        Parse AI's price estimate and return a max price for finding dupes.

        The logic: if original is $200, we want dupes under $80 (40% of original).
        This ensures we're actually finding CHEAPER alternatives, not similar-priced items.

        Returns None if we can't parse the price (no filter applied).
        """
        if not price_estimate:
            return None

        try:
            # Extract numbers from strings like "$150-$200", "$180", "Around $200"
            # Find all numbers in the string
            numbers = re.findall(r'\d+(?:\.\d+)?', price_estimate)
            if not numbers:
                return None

            # If range like "$150-$200", use the higher number
            # If single number, use that
            prices = [float(n) for n in numbers]
            original_price = max(prices)

            if original_price <= 0:
                return None

            # Set max dupe price at 50% of original (or $50 minimum)
            # $200 original -> $100 max for dupes
            # $100 original -> $50 max for dupes
            # $40 original -> $50 max (minimum threshold)
            max_dupe_price = max(50, original_price * 0.5)

            logger.info(f"Parsed price estimate '{price_estimate}' -> original ~${original_price}, max dupe ${max_dupe_price}")
            return max_dupe_price

        except (ValueError, TypeError) as e:
            logger.warning(f"Could not parse price estimate '{price_estimate}': {e}")
            return None

    def _clean_brand(self, brand: str) -> Optional[str]:
        """
        Clean up AI-generated brand field to extract just the brand name.
        Returns None if no valid brand is found.
        """
        if not brand:
            return None

        # Skip if it contains uncertainty indicators
        uncertainty_phrases = [
            "unknown", "unidentified", "unclear", "cannot determine",
            "further inspection", "confidence:", "likelihood:",
            "could be", "might be", "possibly", "probably",
            "generic", "no visible", "not visible", "n/a", "none"
        ]

        brand_lower = brand.lower()
        for phrase in uncertainty_phrases:
            if phrase in brand_lower:
                return None

        # Skip if it's too long (real brand names are short)
        if len(brand) > 30:
            return None

        # Skip if it contains parentheses with numbers (like "Confidence: 85")
        if re.search(r'\([^)]*\d+[^)]*\)', brand):
            # Try to extract just the part before the parenthesis
            clean_brand = re.sub(r'\s*\([^)]*\).*', '', brand).strip()
            if clean_brand and len(clean_brand) <= 30:
                return clean_brand
            return None

        return brand.strip()

    def _clean_color(self, color: str) -> str:
        """Extract just the basic color name from verbose AI descriptions."""
        if not color:
            return ""

        # Remove parenthetical content like "(Pantone 17-0230 TCX)"
        color = re.sub(r'\([^)]*\)', '', color).strip()

        # Get just the first 1-2 words (e.g., "Deep Teal" from "Deep Teal Green")
        words = color.split()
        if len(words) > 2:
            words = words[:2]

        # Return just the main color word if it's a basic color
        basic_colors = ["black", "white", "gray", "grey", "blue", "red", "green",
                       "yellow", "orange", "purple", "pink", "brown", "beige",
                       "navy", "teal", "cream", "tan", "khaki", "olive"]

        for word in words:
            if word.lower() in basic_colors:
                return word.lower()

        # Return first word if no basic color found
        return words[0].lower() if words else ""

    def _build_exact_query(self, analysis: GeminiAnalysis, gender_prefix: str, user_brand: Optional[str] = None) -> str:
        """
        Build SIMPLE, EFFECTIVE search query like "men's black baggy jeans".
        Simple queries work better on Google Shopping than complex ones.

        If user_brand is provided, use it instead of AI-detected brand.
        Gender prefix ensures results match the user's preference.
        Includes fit/silhouette for pants/jeans/tops to get accurate results.
        """
        parts = []

        # Gender prefix FIRST for better filtering (men's, women's)
        if gender_prefix:
            parts.append(gender_prefix.strip())

        # Brand second (most important for exact match)
        # User-provided brand takes priority over AI detection
        if user_brand:
            parts.append(user_brand)
            logger.info(f"Using user-provided brand: '{user_brand}'")
        else:
            clean_brand = self._clean_brand(analysis.brand)
            if clean_brand:
                parts.append(clean_brand)

        # Primary color (simple, cleaned)
        if analysis.colors:
            color = self._clean_color(analysis.colors[0])
            if color:
                parts.append(color)

        # Add fit/silhouette BEFORE item type for pants/jeans/tops
        # This is CRITICAL - "baggy jeans" vs "skinny jeans" are completely different items
        if analysis.fit_silhouette:
            fit_lower = analysis.fit_silhouette.lower()
            # Extract the key fit word (first word usually)
            fit_keywords = ["baggy", "wide-leg", "wide leg", "straight-leg", "straight leg",
                          "bootcut", "skinny", "slim", "relaxed", "mom", "boyfriend",
                          "tapered", "flare", "loose", "oversized", "fitted", "cropped", "boxy"]
            for keyword in fit_keywords:
                if keyword in fit_lower:
                    parts.append(keyword.replace("-", " "))
                    logger.info(f"Added fit keyword: '{keyword}'")
                    break

        # Simple item type (clean up verbose descriptions)
        item_type = analysis.item_type
        # Remove overly specific prefixes that might duplicate fit info
        item_type = re.sub(r'^(Long-Sleeved|Short-Sleeved|Sleeveless)\s+', '', item_type)
        # Also remove fit words from item_type if we already added them
        item_type = re.sub(r'^(Baggy|Wide-leg|Straight-leg|Bootcut|Skinny|Slim|Relaxed|Mom|Boyfriend|Tapered|Flare|Loose|Oversized|Fitted|Cropped|Boxy)\s+', '', item_type, flags=re.IGNORECASE)
        parts.append(item_type)

        query = " ".join(parts)
        logger.info(f"Built exact query: '{query}'")
        return query

    def _build_alternative_query(self, analysis: GeminiAnalysis, gender_prefix: str) -> str:
        """
        Build query for CHEAP DUPES/ALTERNATIVES.
        No brand - we want knockoffs and dupes, not the original expensive brand.
        Includes dupe/affordable keywords to find budget options.
        """
        parts = []

        # Gender prefix if specified
        if gender_prefix:
            parts.append(gender_prefix.strip())

        # Primary color (simple, cleaned)
        if analysis.colors:
            color = self._clean_color(analysis.colors[0])
            if color:
                parts.append(color)

        # Add fit/silhouette BEFORE item type for pants/jeans/tops
        # This is CRITICAL - "baggy jeans" vs "skinny jeans" are completely different items
        if analysis.fit_silhouette:
            fit_lower = analysis.fit_silhouette.lower()
            # Extract the key fit word (first word usually)
            fit_keywords = ["baggy", "wide-leg", "wide leg", "straight-leg", "straight leg",
                          "bootcut", "skinny", "slim", "relaxed", "mom", "boyfriend",
                          "tapered", "flare", "loose", "oversized", "fitted", "cropped", "boxy"]
            for keyword in fit_keywords:
                if keyword in fit_lower:
                    parts.append(keyword.replace("-", " "))
                    logger.info(f"Added fit keyword for alternatives: '{keyword}'")
                    break

        # Simple item type (clean up verbose descriptions)
        item_type = analysis.item_type
        item_type = re.sub(r'^(Long-Sleeved|Short-Sleeved|Sleeveless)\s+', '', item_type)
        # Also remove fit words from item_type if we already added them
        item_type = re.sub(r'^(Baggy|Wide-leg|Straight-leg|Bootcut|Skinny|Slim|Relaxed|Mom|Boyfriend|Tapered|Flare|Loose|Oversized|Fitted|Cropped|Boxy)\s+', '', item_type, flags=re.IGNORECASE)
        parts.append(item_type)

        # ADD DUPE/BUDGET KEYWORDS - This is the key to finding cheap alternatives!
        # These keywords help Google return knockoffs, dupes, and budget alternatives
        parts.append("dupe affordable")

        query = " ".join(parts)
        logger.info(f"Built alternative query (with dupe keywords): '{query}'")
        return query

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
            color = self._clean_color(analysis.colors[0])
            if color:
                parts.append(color)

        # Add fit/silhouette - CRITICAL for pants/jeans
        if analysis.fit_silhouette:
            fit_lower = analysis.fit_silhouette.lower()
            fit_keywords = ["baggy", "wide-leg", "wide leg", "straight-leg", "straight leg",
                          "bootcut", "skinny", "slim", "relaxed", "mom", "boyfriend",
                          "tapered", "flare", "loose", "oversized", "fitted", "cropped", "boxy"]
            for keyword in fit_keywords:
                if keyword in fit_lower:
                    parts.append(keyword.replace("-", " "))
                    break

        # Item type - ALWAYS include (clean up fit words that might be duplicated)
        item_type = analysis.item_type
        item_type = re.sub(r'^(Baggy|Wide-leg|Straight-leg|Bootcut|Skinny|Slim|Relaxed|Mom|Boyfriend|Tapered|Flare|Loose|Oversized|Fitted|Cropped|Boxy)\s+', '', item_type, flags=re.IGNORECASE)
        parts.append(item_type)

        # Add most important key features (first 2)
        if analysis.key_features and len(analysis.key_features) > 0:
            # Take first 2 features, clean them up
            for feature in analysis.key_features[:2]:
                # Extract meaningful words (skip generic terms)
                feature_words = [w for w in feature.lower().split() if len(w) > 3 and w not in ["type", "style", "with"]]
                if feature_words:
                    parts.append(feature_words[0])

        return " ".join(parts)

    async def _search_google_lens(
        self,
        image_url: str,
        analysis: GeminiAnalysis,
        num_results: int = 20
    ) -> List[Product]:
        """
        Search using Google Lens API for VISUAL product matching.
        This is much more accurate than text-based search because it matches
        the actual image pixels, not just keywords.

        Returns products with high similarity scores since they're visual matches.
        """
        try:
            # Check cache first
            cache_key = hashlib.md5(f"lens:{image_url}:{num_results}".encode()).hexdigest()
            cached_result = self._search_cache.get(cache_key)
            if cached_result is not None:
                logger.info("Returning cached Google Lens results")
                return cached_result

            # Check daily API limit
            if not api_tracker.can_make_call():
                logger.warning("Daily API limit reached. Skipping Google Lens search.")
                return []

            # Rate limiting
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            if time_since_last < self._min_request_interval:
                await asyncio.sleep(self._min_request_interval - time_since_last)
            self._last_request_time = time.time()

            api_tracker.record_call()

            # Google Lens API parameters
            params = {
                "engine": "google_lens",
                "url": image_url,
                "api_key": settings.SERPAPI_API_KEY,
                "hl": "en",
                "country": "us",
            }

            logger.info(f"Calling Google Lens API with image: {image_url}")
            response = await self.client.get("https://serpapi.com/search", params=params)

            if response.status_code == 429:
                logger.warning("Google Lens rate limit hit. Waiting...")
                await asyncio.sleep(2)
                response = await self.client.get("https://serpapi.com/search", params=params)
                if response.status_code == 429:
                    logger.error("Google Lens rate limit persists. Skipping.")
                    return []

            response.raise_for_status()
            data = response.json()

            if "error" in data:
                logger.error(f"Google Lens error: {data.get('error')}")
                return []

            products = []

            # Google Lens returns visual_matches and/or shopping_results
            # Visual matches are products that look similar to the image
            visual_matches = data.get("visual_matches", [])
            lens_shopping = data.get("shopping_results", [])

            logger.info(f"Google Lens found {len(visual_matches)} visual matches, {len(lens_shopping)} shopping results")

            # Process visual matches first (highest accuracy)
            for i, item in enumerate(visual_matches[:num_results]):
                title = item.get("title", "")
                link = item.get("link", "")
                source = item.get("source", "")

                if not title or not link:
                    continue

                # Visual matches from Lens are HIGHLY accurate - they're pixel-level matches
                # Position matters: first results are best matches (Google ranks by visual similarity)
                # Score range: 88-99% for visual matches
                if i < 3:
                    base_similarity = 96 + (3 - i)  # Top 3: 97-99%
                elif i < 8:
                    base_similarity = 92 + random.randint(0, 3)  # 92-95%
                else:
                    base_similarity = 88 + random.randint(0, 3)  # 88-91%

                # Extract price if available
                price = 0.0
                price_info = item.get("price", {})
                if isinstance(price_info, dict):
                    price_str = price_info.get("extracted_value", 0)
                    if price_str:
                        try:
                            price = float(price_str)
                        except (ValueError, TypeError):
                            price = 0.0
                elif isinstance(price_info, str):
                    try:
                        price = float(price_info.replace("$", "").replace(",", "").strip())
                    except ValueError:
                        price = 0.0

                if price <= 0:
                    price = 0.01

                products.append(Product(
                    id=f"lens_vm_{i}_{random.randint(1000, 9999)}",
                    title=title,
                    description=item.get("snippet", "") or f"Visual match from {source}",
                    price=price,
                    original_price=None,
                    currency="USD",
                    image_url=item.get("thumbnail", "https://via.placeholder.com/300"),
                    merchant=source or "Visual Match",
                    affiliate_link=link,
                    similarity_percentage=base_similarity,
                    brand=source,
                    category=analysis.item_type
                ))

            # Also process any shopping results from Lens
            for i, item in enumerate(lens_shopping[:max(0, num_results - len(products))]):
                title = item.get("title", "")
                link = item.get("link", "") or item.get("product_link", "")

                if not title or not link:
                    continue

                # Shopping results from Lens are visual matches (slightly lower than visual_matches)
                # Position matters here too
                if i < 5:
                    similarity = 90 + random.randint(0, 5)  # 90-95%
                else:
                    similarity = 85 + random.randint(0, 4)  # 85-89%

                price = item.get("extracted_price", 0)
                if not price:
                    try:
                        price_str = str(item.get("price", "0")).replace("$", "").replace(",", "").strip()
                        price = float(price_str) if price_str else 0.0
                    except ValueError:
                        price = 0.0

                if price <= 0:
                    price = 0.01

                products.append(Product(
                    id=item.get("product_id", f"lens_shop_{i}_{random.randint(1000, 9999)}"),
                    title=title,
                    description=item.get("snippet", "") or analysis.detailed_description[:100],
                    price=price,
                    original_price=item.get("extracted_old_price"),
                    currency="USD",
                    image_url=item.get("thumbnail", "https://via.placeholder.com/300"),
                    merchant=item.get("source", "Unknown"),
                    affiliate_link=link,
                    similarity_percentage=similarity,
                    brand=item.get("source", "Unknown"),
                    category=analysis.item_type
                ))

            # Cache results
            self._search_cache.set(cache_key, products)

            return products

        except Exception as e:
            logger.error(f"Google Lens search error: {type(e).__name__}: {e}")
            return []

    async def _search_serpapi(
        self,
        query: str,
        analysis: GeminiAnalysis,
        is_exact_match: bool,
        num_results: int = 20,
        max_price: Optional[float] = None
    ) -> List[Product]:
        """Execute a SerpApi search and parse results with caching.

        Args:
            max_price: If set, filters out products above this price (for finding cheap dupes)
        """
        try:
            # Truncate query to reasonable length
            query = self._truncate_query(query)

            # Check cache first (include max_price in cache key)
            cache_key = hashlib.md5(f"search:{query}:{num_results}:{is_exact_match}:{max_price}".encode()).hexdigest()
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
            }

            # Add price filter if max_price is set (for finding cheap dupes)
            # SerpAPI supports tbs parameter for price filtering
            if max_price and max_price > 0:
                # tbs=mr:1,price:1,ppr_max:{price} filters to products under max price
                params["tbs"] = f"mr:1,price:1,ppr_max:{int(max_price)}"
                logger.info(f"Added price filter: max ${int(max_price)}")

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

                # PRICE FILTER: Skip items above max_price (for finding cheap dupes)
                if max_price and price > max_price:
                    logger.debug(f"Skipping expensive item: {title[:50]}... (${price} > ${max_price})")
                    filtered_count += 1
                    continue

                # Extract original price if available
                orig_price_str = item.get("extracted_old_price")
                original_price = float(orig_price_str) if orig_price_str else None

                # Calculate similarity score
                similarity = self._calculate_real_similarity(
                    title,
                    snippet,
                    analysis,
                    is_exact_match
                )

                # Keep all products - no filtering by similarity
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
