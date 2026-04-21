"""Google Custom Search Engine (CSE) service for product search.

This is a MUCH CHEAPER alternative to SerpAPI:
- SerpAPI: $50/month for 5,000 searches ($0.01 per search)
- Google CSE: $5 per 1,000 searches after free tier ($0.005 per search)
- Free tier: 100 searches/day

Setup instructions:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create an API key
3. Enable "Custom Search API" in your project
4. Go to https://programmablesearchengine.google.com/
5. Create a new search engine
6. Configure it to search shopping sites (see SHOPPING_SITES below)
7. Copy the Search Engine ID (cx parameter)
"""
import logging
import httpx
import random
import asyncio
import re
from typing import List, Dict, Any, Optional
from ..config import settings
from ..schemas import Product, GeminiAnalysis

logger = logging.getLogger(__name__)

# Shopping sites to include in Custom Search Engine
# When creating your CSE, add these sites to get shopping results
SHOPPING_SITES = [
    "amazon.com",
    "walmart.com",
    "target.com",
    "nordstrom.com",
    "macys.com",
    "zappos.com",
    "asos.com",
    "hm.com",
    "zara.com",
    "uniqlo.com",
    "gap.com",
    "oldnavy.com",
    "forever21.com",
    "urbanoutfitters.com",
    "anthropologie.com",
    "freepeople.com",
    "revolve.com",
    "shopbop.com",
    "ssense.com",
    "farfetch.com",
    "net-a-porter.com",
    "bloomingdales.com",
    "saksoff5th.com",
    "ebay.com",
    "poshmark.com",
    "depop.com",
    "thredup.com",
    "shein.com",
    "boohoo.com",
    "prettylittlething.com",
    "fashionnova.com",
]


class GoogleCSEService:
    """Google Custom Search Engine service for product search.

    This service provides a cost-effective alternative to SerpAPI
    for searching products across major retailers.
    """

    # API endpoint
    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    # Rate limiting
    MIN_REQUEST_INTERVAL = 0.5  # 500ms between requests

    def __init__(self):
        """Initialize the Google CSE service."""
        self.client = httpx.AsyncClient(timeout=30.0)
        self._last_request_time = 0
        self._daily_calls = 0
        self._daily_limit = 100  # Free tier limit

    def is_configured(self) -> bool:
        """Check if Google CSE is properly configured."""
        return bool(settings.GOOGLE_CSE_API_KEY and settings.GOOGLE_CSE_CX)

    async def search_products(
        self,
        query: str,
        analysis: GeminiAnalysis,
        num_results: int = 10,
        is_exact_match: bool = True
    ) -> List[Product]:
        """
        Search for products using Google Custom Search API.

        Args:
            query: Search query string
            analysis: Gemini analysis for similarity scoring
            num_results: Number of results to return (max 10 per request)
            is_exact_match: Whether this is an exact match search

        Returns:
            List of Product objects
        """
        if not self.is_configured():
            logger.warning("Google CSE not configured. Skipping search.")
            return []

        try:
            # Rate limiting
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self._last_request_time
            if time_since_last < self.MIN_REQUEST_INTERVAL:
                await asyncio.sleep(self.MIN_REQUEST_INTERVAL - time_since_last)
            self._last_request_time = asyncio.get_event_loop().time()

            # Truncate query to reasonable length
            query = query[:100].strip()

            params = {
                "key": settings.GOOGLE_CSE_API_KEY,
                "cx": settings.GOOGLE_CSE_CX,
                "q": query,
                "num": min(num_results, 10),  # Max 10 per request
                "searchType": "image" if is_exact_match else None,  # Image search for exact matches
            }

            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}

            logger.info(f"Google CSE search: '{query}'")
            response = await self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()

            data = response.json()
            self._daily_calls += 1

            items = data.get("items", [])
            logger.info(f"Google CSE returned {len(items)} results")

            products = []
            for i, item in enumerate(items):
                product = self._parse_search_result(item, i, analysis, is_exact_match)
                if product:
                    products.append(product)

            return products

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Google CSE rate limit reached")
            elif e.response.status_code == 403:
                logger.error("Google CSE API key invalid or quota exceeded")
            else:
                logger.error(f"Google CSE HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Google CSE error: {e}")
            return []

    def _parse_search_result(
        self,
        item: Dict[str, Any],
        index: int,
        analysis: GeminiAnalysis,
        is_exact_match: bool
    ) -> Optional[Product]:
        """Parse a Google CSE search result into a Product."""
        try:
            title = item.get("title", "")
            link = item.get("link", "")
            snippet = item.get("snippet", "")

            if not title or not link:
                return None

            # Extract image URL
            image_url = "https://via.placeholder.com/300"
            if "pagemap" in item:
                pagemap = item["pagemap"]
                if "cse_image" in pagemap and pagemap["cse_image"]:
                    image_url = pagemap["cse_image"][0].get("src", image_url)
                elif "cse_thumbnail" in pagemap and pagemap["cse_thumbnail"]:
                    image_url = pagemap["cse_thumbnail"][0].get("src", image_url)

            # Extract price from snippet or metatags
            price = self._extract_price(item)

            # Extract merchant from display link
            display_link = item.get("displayLink", "")
            merchant = display_link.replace("www.", "").split(".")[0].title()

            # Calculate similarity score
            similarity = self._calculate_similarity(title, snippet, analysis, is_exact_match, index)

            return Product(
                id=f"gcse_{index}_{random.randint(1000, 9999)}",
                title=title,
                description=snippet or analysis.detailed_description[:100],
                price=price if price > 0 else -1,
                original_price=None,
                currency="USD",
                image_url=image_url,
                merchant=merchant or "Unknown",
                affiliate_link=link,
                similarity_percentage=similarity,
                brand=merchant,
                category=analysis.item_type,
                rating=None,
                reviews_count=None
            )
        except Exception as e:
            logger.warning(f"Error parsing CSE result: {e}")
            return None

    def _extract_price(self, item: Dict[str, Any]) -> float:
        """Extract price from search result."""
        try:
            # Try metatags first
            if "pagemap" in item and "metatags" in item["pagemap"]:
                for metatag in item["pagemap"]["metatags"]:
                    for key in ["og:price:amount", "product:price:amount", "price"]:
                        if key in metatag:
                            price_str = metatag[key]
                            return float(re.sub(r'[^\d.]', '', str(price_str)))

            # Try snippet
            snippet = item.get("snippet", "")
            price_match = re.search(r'\$(\d+(?:\.\d{2})?)', snippet)
            if price_match:
                return float(price_match.group(1))

            return 0.0
        except (ValueError, TypeError):
            return 0.0

    def _calculate_similarity(
        self,
        title: str,
        snippet: str,
        analysis: GeminiAnalysis,
        is_exact_match: bool,
        index: int
    ) -> int:
        """Calculate similarity score based on attribute matching."""
        title_lower = title.lower()
        snippet_lower = snippet.lower()
        combined = f"{title_lower} {snippet_lower}"

        score = 60  # Base score for Google results

        # Brand match (+15)
        if analysis.brand:
            brand_lower = analysis.brand.lower()
            if brand_lower in combined:
                score += 15

        # Item type match (+15)
        item_words = [w for w in analysis.item_type.lower().split() if len(w) > 3]
        if any(word in combined for word in item_words):
            score += 15

        # Color match (+10)
        if analysis.colors:
            primary_color = analysis.colors[0].lower()
            if primary_color in combined:
                score += 10

        # Position bonus (first results are typically more relevant)
        if index < 3:
            score += 5

        # Exact match mode bonus
        if is_exact_match:
            score += 5

        return min(95, max(55, score))

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "configured": self.is_configured(),
            "daily_calls": self._daily_calls,
            "daily_limit": self._daily_limit,
            "remaining": max(0, self._daily_limit - self._daily_calls)
        }


# Singleton instance
google_cse_service = GoogleCSEService()
