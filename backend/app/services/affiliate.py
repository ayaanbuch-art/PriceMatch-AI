"""Affiliate link service for monetizing product links.

Supports multiple affiliate networks:
- Skimlinks (universal - works with 48,000+ merchants)
- Amazon Associates (direct)
- Sovrn Commerce (alternative universal network)

The affiliate conversion happens AFTER search results are found,
so it does NOT affect search quality in any way.
"""
import logging
from typing import Optional, List, Any
from urllib.parse import quote_plus
from ..config import settings

logger = logging.getLogger(__name__)


class AffiliateService:
    """Service for converting product URLs to affiliate links.

    IMPORTANT: This service only wraps existing URLs with tracking.
    It does NOT affect search results, ranking, or quality in any way.
    The affiliate conversion happens as the LAST step before returning results.
    """

    def convert_to_affiliate_link(self, product_url: str, merchant: str = "") -> str:
        """
        Convert a product URL to an affiliate link.

        Priority:
        1. Skimlinks (universal - if configured)
        2. Amazon Associates (if Amazon URL and configured)
        3. Sovrn Commerce (alternative universal)
        4. Original URL (fallback)

        Args:
            product_url: The original product URL
            merchant: The merchant name (for logging/analytics)

        Returns:
            Affiliate-enabled URL (or original if no affiliate configured)
        """
        if not product_url:
            return product_url

        # Option 1: Skimlinks (universal affiliate network)
        # Works with Amazon, Target, Walmart, Nordstrom, ASOS, and 48,000+ other merchants
        if settings.SKIMLINKS_PUBLISHER_ID:
            affiliate_url = self._convert_skimlinks(product_url)
            logger.debug(f"Converted to Skimlinks affiliate: {merchant}")
            return affiliate_url

        # Option 2: Amazon Associates (direct, if Amazon URL)
        if "amazon" in product_url.lower() and settings.AMAZON_ASSOCIATE_TAG:
            affiliate_url = self._convert_amazon(product_url)
            logger.debug(f"Converted to Amazon Associates affiliate")
            return affiliate_url

        # Option 3: Sovrn Commerce (alternative to Skimlinks)
        if settings.SOVRN_PUBLISHER_ID:
            affiliate_url = self._convert_sovrn(product_url)
            logger.debug(f"Converted to Sovrn affiliate: {merchant}")
            return affiliate_url

        # No affiliate configured - return original URL
        return product_url

    def _convert_skimlinks(self, url: str) -> str:
        """
        Convert URL using Skimlinks.

        Skimlinks automatically:
        - Detects the merchant
        - Applies the best affiliate program
        - Tracks clicks and conversions
        - Pays you monthly
        """
        encoded_url = quote_plus(url)
        return f"https://go.skimresources.com?id={settings.SKIMLINKS_PUBLISHER_ID}&url={encoded_url}"

    def _convert_amazon(self, url: str) -> str:
        """Convert Amazon URL with Associates tag."""
        if "?" in url:
            return f"{url}&tag={settings.AMAZON_ASSOCIATE_TAG}"
        else:
            return f"{url}?tag={settings.AMAZON_ASSOCIATE_TAG}"

    def _convert_sovrn(self, url: str) -> str:
        """Convert URL using Sovrn Commerce (VigLink)."""
        encoded_url = quote_plus(url)
        return f"https://redirect.viglink.com?key={settings.SOVRN_PUBLISHER_ID}&u={encoded_url}"

    def convert_product_list(self, products: List[Any]) -> List[Any]:
        """
        Convert all product URLs in a list to affiliate links.

        This is the main method called from product_search.py
        AFTER all search and ranking is complete.

        Args:
            products: List of Product objects with 'affiliate_link' field

        Returns:
            Same list with affiliate_link fields converted
        """
        if not self.is_affiliate_enabled():
            return products

        for product in products:
            if hasattr(product, 'affiliate_link'):
                # Pydantic model - need to create new object since it's frozen
                original_url = product.affiliate_link
                merchant = getattr(product, 'merchant', '')
                # Note: Product objects are typically mutable in this codebase
                try:
                    product.affiliate_link = self.convert_to_affiliate_link(original_url, merchant)
                except Exception:
                    # If product is frozen, we'll handle it in the caller
                    pass
            elif isinstance(product, dict) and 'affiliate_link' in product:
                # Dictionary
                original_url = product['affiliate_link']
                merchant = product.get('merchant', '')
                product['affiliate_link'] = self.convert_to_affiliate_link(original_url, merchant)

        return products

    def is_affiliate_enabled(self) -> bool:
        """Check if any affiliate network is configured."""
        return bool(
            settings.SKIMLINKS_PUBLISHER_ID or
            settings.AMAZON_ASSOCIATE_TAG or
            settings.SOVRN_PUBLISHER_ID
        )

    def get_affiliate_stats(self) -> dict:
        """Return info about configured affiliate networks."""
        return {
            "skimlinks_enabled": bool(settings.SKIMLINKS_PUBLISHER_ID),
            "amazon_enabled": bool(settings.AMAZON_ASSOCIATE_TAG),
            "sovrn_enabled": bool(settings.SOVRN_PUBLISHER_ID),
            "any_enabled": self.is_affiliate_enabled()
        }

    # Legacy method for backwards compatibility
    def generate_affiliate_link(
        self,
        merchant: str,
        product_url: str,
        product_id: str
    ) -> str:
        """Legacy method - use convert_to_affiliate_link instead."""
        return self.convert_to_affiliate_link(product_url, merchant)

    async def track_click(
        self,
        user_id: int,
        product_id: str,
        affiliate_link: str
    ) -> bool:
        """
        Track an affiliate link click.
        Note: Skimlinks/Sovrn handle tracking automatically.
        This is for internal analytics only.
        """
        # Skimlinks and Sovrn track clicks automatically via their redirect
        # This method is for internal analytics if needed
        logger.info(f"Affiliate click: user={user_id}, product={product_id}")
        return True


# Singleton instance
affiliate_service = AffiliateService()
