"""Search result caching service to reduce API costs.

This cache stores search results so similar/identical searches
don't require new API calls. This can reduce SerpAPI costs by 40-60%.

Cache strategy:
- Cache by normalized search query (item_type + colors + brand + style)
- 24-hour TTL (prices don't change that frequently)
- Memory-based with optional file persistence
"""
import logging
import hashlib
import json
import time
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from ..config import settings

logger = logging.getLogger(__name__)


class SearchCache:
    """Cache for search results to reduce API costs.

    Uses a two-tier caching strategy:
    1. Memory cache (fast, volatile)
    2. File cache (persistent across restarts)
    """

    def __init__(self, ttl_seconds: Optional[int] = None, cache_dir: str = "/tmp/pricematch_cache"):
        """
        Initialize the search cache.

        Args:
            ttl_seconds: Time-to-live for cache entries (default from settings)
            cache_dir: Directory for file-based cache persistence
        """
        self._ttl = ttl_seconds or settings.SEARCH_CACHE_TTL_SECONDS
        self._memory_cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_dir = Path(cache_dir)
        self._stats = {
            "hits": 0,
            "misses": 0,
            "saves": 0
        }

        # Create cache directory if it doesn't exist
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create cache directory: {e}")

    def _generate_cache_key(
        self,
        item_type: str,
        colors: List[str],
        brand: Optional[str],
        style: Optional[str],
        gender: str,
        search_mode: str
    ) -> str:
        """
        Generate a unique cache key from search parameters.

        The key is based on the essential search characteristics,
        so similar searches can share cached results.
        """
        # Normalize inputs
        normalized_colors = sorted([c.lower().strip() for c in colors]) if colors else []
        normalized_brand = (brand or "").lower().strip()
        normalized_style = (style or "").lower().strip()
        normalized_item_type = item_type.lower().strip()

        # Build key components
        key_parts = [
            normalized_item_type,
            "-".join(normalized_colors[:3]),  # Max 3 colors
            normalized_brand[:50] if normalized_brand else "nobrand",
            normalized_style[:30] if normalized_style else "nostyle",
            gender,
            search_mode
        ]

        key_string = "|".join(key_parts)

        # Hash for consistent length and filesystem safety
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(
        self,
        item_type: str,
        colors: List[str],
        brand: Optional[str] = None,
        style: Optional[str] = None,
        gender: str = "either",
        search_mode: str = "exact"
    ) -> Optional[List[Dict]]:
        """
        Get cached search results if available and not expired.

        Args:
            item_type: Type of clothing item
            colors: List of colors
            brand: Brand name (optional)
            style: Style description (optional)
            gender: 'male', 'female', or 'either'
            search_mode: 'exact' or 'alternatives'

        Returns:
            Cached product list or None if not cached/expired
        """
        cache_key = self._generate_cache_key(
            item_type, colors, brand, style, gender, search_mode
        )

        # Check memory cache first (fastest)
        if cache_key in self._memory_cache:
            data, timestamp = self._memory_cache[cache_key]
            if time.time() - timestamp < self._ttl:
                self._stats["hits"] += 1
                logger.info(f"Cache HIT (memory): {cache_key[:8]}... ({len(data)} products)")
                return data
            else:
                del self._memory_cache[cache_key]

        # Check file cache (slower but persistent)
        cache_file = self._cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached = json.load(f)

                if time.time() - cached.get('timestamp', 0) < self._ttl:
                    products = cached.get('products', [])
                    # Warm up memory cache
                    self._memory_cache[cache_key] = (products, cached['timestamp'])
                    self._stats["hits"] += 1
                    logger.info(f"Cache HIT (file): {cache_key[:8]}... ({len(products)} products)")
                    return products
                else:
                    # Expired, remove file
                    cache_file.unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Error reading cache file: {e}")

        self._stats["misses"] += 1
        logger.debug(f"Cache MISS: {cache_key[:8]}...")
        return None

    def set(
        self,
        item_type: str,
        colors: List[str],
        products: List[Dict],
        brand: Optional[str] = None,
        style: Optional[str] = None,
        gender: str = "either",
        search_mode: str = "exact"
    ) -> None:
        """
        Cache search results.

        Args:
            item_type: Type of clothing item
            colors: List of colors
            products: List of product dictionaries to cache
            brand: Brand name (optional)
            style: Style description (optional)
            gender: 'male', 'female', or 'either'
            search_mode: 'exact' or 'alternatives'
        """
        if not products:
            return  # Don't cache empty results

        cache_key = self._generate_cache_key(
            item_type, colors, brand, style, gender, search_mode
        )

        current_time = time.time()

        # Store in memory cache
        self._memory_cache[cache_key] = (products, current_time)

        # Store in file cache (persistent)
        cache_file = self._cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    'timestamp': current_time,
                    'products': products,
                    'metadata': {
                        'item_type': item_type,
                        'colors': colors,
                        'brand': brand,
                        'style': style,
                        'gender': gender,
                        'search_mode': search_mode
                    }
                }, f)
            self._stats["saves"] += 1
            logger.info(f"Cached {len(products)} products: {cache_key[:8]}...")
        except Exception as e:
            logger.warning(f"Error writing cache file: {e}")

    def clear(self) -> int:
        """Clear all cached data. Returns count of entries cleared."""
        count = len(self._memory_cache)
        self._memory_cache.clear()

        # Clear file cache
        try:
            for cache_file in self._cache_dir.glob("*.json"):
                cache_file.unlink()
                count += 1
        except Exception as e:
            logger.warning(f"Error clearing file cache: {e}")

        return count

    def clear_expired(self) -> int:
        """Remove expired entries. Returns count of entries cleared."""
        current_time = time.time()
        count = 0

        # Clear expired memory cache
        expired_keys = [
            k for k, (_, ts) in self._memory_cache.items()
            if current_time - ts >= self._ttl
        ]
        for key in expired_keys:
            del self._memory_cache[key]
            count += 1

        # Clear expired file cache
        try:
            for cache_file in self._cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r') as f:
                        cached = json.load(f)
                    if current_time - cached.get('timestamp', 0) >= self._ttl:
                        cache_file.unlink()
                        count += 1
                except Exception:
                    # If we can't read it, delete it
                    cache_file.unlink(missing_ok=True)
                    count += 1
        except Exception as e:
            logger.warning(f"Error clearing expired files: {e}")

        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "saves": self._stats["saves"],
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 1),
            "memory_entries": len(self._memory_cache),
            "ttl_seconds": self._ttl,
            "estimated_savings_percent": round(hit_rate * 0.9, 1)  # Rough estimate
        }


# Singleton instance
search_cache = SearchCache()
