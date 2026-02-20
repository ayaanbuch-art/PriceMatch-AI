"""Google Gemini AI integration service with tier-based enhancements."""
import logging
import google.generativeai as genai
import json
from typing import Dict, Any, Optional
from fastapi import HTTPException

from ..config import settings
from ..schemas import GeminiAnalysis

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for interacting with Google Gemini Vision API with tier-based analysis."""

    def __init__(self):
        """Initialize Gemini service."""
        try:
            genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)
            model_name = 'gemini-2.0-flash'
            self.model = genai.GenerativeModel(model_name)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize AI service"
            )

    def _get_tier_prompt(self, tier: str = "free", search_mode: str = "alternatives") -> str:
        """Get the appropriate analysis prompt based on subscription tier and search mode."""

        # Search mode specific context
        if search_mode == "exact":
            search_context = """
SEARCH MODE: EXACT MATCH
The user wants to find THIS EXACT ITEM online.
CRITICAL: Focus heavily on:
- Brand identification (look for logos, labels, tags, distinctive design elements)
- Specific model/product name if visible
- Unique identifying features that distinguish this from similar items
- Model number, SKU, or version if identifiable

Look VERY carefully for any visible brand logos, labels, tags, text, packaging, or distinctive brand design elements.

SEARCH TERM PRIORITY: Generate search terms that will find the EXACT product:
- Include brand name + model if known
- Include specific product codes or model names if visible
- Use exact descriptors (e.g., "Sony WH-1000XM5 black headphones" not just "wireless headphones")
"""
        else:
            search_context = """
SEARCH MODE: FIND ALTERNATIVES
The user wants to find SIMILAR items or CHEAPER ALTERNATIVES.
Focus on identifying the style, design, and key features so we can find comparable items across different brands and price points.

Look carefully for any visible brand logos, labels, or distinctive design elements - this helps find alternatives at different price points.

SEARCH TERM PRIORITY: Generate search terms that will find SIMILAR items and ALTERNATIVES:
- Focus on descriptive terms (e.g., "noise cancelling over-ear headphones", "minimalist desk lamp")
- Include general category terms for broader results
- Include style descriptors for better matching
"""

        # =============================================================================
        # FREE PLAN – "Smart Basic Finder"
        # Goal: Good results. Solid value. Fast.
        # Positioning: Useful and reliable, but not deeply personalized.
        # =============================================================================
        if tier == "free":
            return f"""You are a product analysis AI.
The user has uploaded an image of an item.

{search_context}

Your tasks:
1. Identify the item (type, category, style, material if visible).
2. Estimate the likely brand tier (luxury, mid-range, budget, unknown).
3. Describe key visual features clearly.
4. Find 5–8 similar items that:
   - Match the style closely
   - Cost less than the estimated original
   - Have strong value (good reviews or good materials for price)
5. Rank the results by best value.

Respond in JSON format:
{{
    "item_type": "specific type (e.g., 'wireless headphones', 'desk lamp', 'sneakers', 'backpack')",
    "brand": "brand name if visible, or null if unknown",
    "style": "style/design category (e.g., 'modern', 'vintage', 'minimalist', 'casual')",
    "detailed_description": "2-3 sentence item summary covering key features",
    "colors": ["primary color", "secondary color"],
    "material": "material type if identifiable",
    "key_features": ["feature 1", "feature 2", "feature 3", "feature 4", "feature 5"],
    "estimated_brand_tier": "luxury/premium/mid-range/budget",
    "season_occasion": "when/where to use this",
    "search_terms": ["keyword 1", "keyword 2", "keyword 3", "keyword 4", "keyword 5"],
    "price_estimate": "estimated price range in USD",
    "why_good_value": "brief explanation of what makes alternatives good value"
}}

Provide accurate, helpful information for finding {"this exact item" if search_mode == "exact" else "similar items at better prices"}."""

        # =============================================================================
        # $4.99 PLAN – "Value Intelligence"
        # Upgrade Difference: Better comparison logic + quality analysis.
        # =============================================================================
        elif tier == "basic":
            return f"""You are an advanced product intelligence AI trained in price-to-quality analysis.
The user uploaded an image of an item.

{search_context}

Your tasks:
1. Identify the item in detail (style category, era influence, material clues, construction clues).
2. Reverse-engineer what makes the item expensive (brand markup, materials, design, trend factor).
3. Estimate realistic retail value.
4. Find 8–12 alternatives that:
   - Match aesthetic ≥ 85% similarity
   - Cost less
   - Offer equal or better material quality OR durability
5. Calculate a Value Score (1–10) based on:
   - Material quality
   - Price fairness
   - Brand markup level
   - Review sentiment
6. Highlight the BEST OVERALL pick and BEST BUDGET pick.

Respond in JSON format:
{{
    "item_type": "specific type with sub-category (e.g., 'over-ear noise-cancelling headphones')",
    "brand": "brand name if visible, or null if unknown",
    "style": "detailed style/design category with era influence",
    "detailed_description": "comprehensive 3-4 sentence description covering design, build quality, notable features",
    "colors": ["primary color with shade", "secondary color", "accent colors"],
    "material": "detailed material analysis with quality assessment",
    "key_features": ["feature 1", "feature 2", "feature 3", "feature 4", "feature 5", "feature 6"],
    "estimated_brand_tier": "luxury/premium/mid-range/budget with reasoning",
    "season_occasion": "detailed use cases",
    "search_terms": ["keyword 1", "keyword 2", "keyword 3", "keyword 4", "keyword 5", "keyword 6", "keyword 7"],
    "price_estimate": "estimated price range with confidence level",
    "why_it_costs_this": "explanation of price factors (brand markup, materials, design, trend)",
    "value_score_factors": {{
        "material_quality": "1-10",
        "price_fairness": "1-10",
        "brand_markup_level": "low/medium/high",
        "overall_value_score": "1-10"
    }},
    "best_overall_pick": "description of best overall alternative",
    "best_budget_pick": "description of best budget alternative",
    "what_you_sacrifice": "what you might give up with alternatives (if anything)",
    "similar_brands": ["brand 1", "brand 2", "brand 3", "brand 4"]
}}

Provide insightful analysis that helps users understand value, not just find products."""

        # =============================================================================
        # $9.99 PLAN – "Personalized Optimization AI"
        # Upgrade Difference: Personalization + strategic advice + use-case optimization.
        # =============================================================================
        elif tier == "pro":
            return f"""You are an elite consumer optimization AI.
The user uploaded an image and may have provided preferences (budget, brands they like, quality priorities, sustainability, etc.).

{search_context}

Your tasks:
1. Fully analyze the item:
   - Construction quality
   - Material probability
   - Target demographic
   - Price psychology
2. Determine whether the original item is overpriced, fairly priced, or underpriced — explain why.
3. Generate 10–15 alternatives segmented into:
   - Best Overall Value
   - Premium Alternative (better quality for slightly less or same price)
   - Budget Steal
   - Trendy Alternative
   - Long-Term Durability Pick
4. Personalize recommendations considering:
   - Typical budget ranges
   - Style preferences
   - Intended use cases
5. Provide a Smart Buyer Strategy:
   - When to buy (seasonal timing)
   - Where to buy
   - Whether to wait for discounts

Respond in JSON format:
{{
    "item_type": "precise type with professional terminology",
    "brand": "brand identification with confidence level",
    "style": "comprehensive style/design analysis with trend context",
    "detailed_description": "thorough 4-5 sentence description covering every visible detail",
    "colors": ["exact color names", "color harmony analysis"],
    "material": "expert material analysis with quality assessment and care notes",
    "key_features": ["feature 1", "feature 2", "feature 3", "feature 4", "feature 5", "feature 6", "feature 7", "feature 8"],
    "estimated_brand_tier": "detailed tier analysis with market positioning",
    "season_occasion": "comprehensive use case guide",
    "search_terms": ["keyword 1", "keyword 2", "keyword 3", "keyword 4", "keyword 5", "keyword 6", "keyword 7", "keyword 8"],
    "price_estimate": "precise price range with market context",
    "price_verdict": "overpriced/fairly_priced/underpriced with detailed explanation",
    "construction_quality": "assessment of build quality and durability",
    "target_demographic": "who this item is designed for",
    "alternatives_segmented": {{
        "best_overall_value": "description and why",
        "premium_alternative": "better quality option",
        "budget_steal": "great value under budget",
        "trendy_alternative": "on-trend option",
        "durability_pick": "long-term investment piece"
    }},
    "smart_buyer_strategy": {{
        "best_time_to_buy": "seasonal timing advice",
        "where_to_buy": "recommended retailers/platforms",
        "wait_for_discount": "true/false with reasoning",
        "negotiation_tips": "if applicable"
    }},
    "styling_tips": ["tip 1", "tip 2", "tip 3", "tip 4", "tip 5"],
    "wardrobe_pairings": ["pairing 1", "pairing 2", "pairing 3", "pairing 4"],
    "trend_context": "how this relates to current trends with longevity prediction",
    "similar_brands": ["brand 1", "brand 2", "brand 3", "brand 4", "brand 5"],
    "final_recommendation": "clear verdict on what to do"
}}

Think like a personal shopping strategist, not just a product finder."""

        # =============================================================================
        # $19.99 PLAN – "Elite AI Shopping Agent"
        # This tier feels like a human luxury personal shopper + financial analyst + trend forecaster combined.
        # Upgrade Difference: Predictive pricing, lifecycle value, resale value, trend forecasting, wardrobe integration.
        # =============================================================================
        else:  # unlimited
            return f"""You are an elite AI shopping agent trained in fashion economics, material science, pricing psychology, resale markets, and trend forecasting.

The user uploaded an item image and may have provided context about their wardrobe, budget, and goals.

{search_context}

Your tasks:
1. Perform forensic-level product analysis:
   - Likely manufacturing cost vs retail markup
   - Brand positioning strategy
   - Trend lifecycle stage (rising, peak, declining, timeless)
   - Material durability prediction
2. Predict:
   - 12-month price trajectory
   - Likelihood of discounting
   - Resale value retention
3. Generate alternatives in strategic tiers:
   - Better Than Original (objectively superior quality)
   - Identical Look, 30–70% Less Cost
   - Long-Term Investment Piece
   - Ultra Budget Hidden Gem
   - Sustainable / Ethical Option
4. Calculate:
   - Cost Per Wear Projection
   - 3-Year Value Index
   - Resale Value Estimate
5. Wardrobe integration suggestions:
   - Full outfit integrations
   - Identify potential redundant purchases
   - Recommend complementary items
6. Provide a decisive verdict:
   - Buy Original
   - Buy Alternative (specify which)
   - Wait
   - Skip Entirely

Respond in JSON format:
{{
    "item_type": "precise type with professional terminology",
    "brand": "brand identification with confidence score (0-100)",
    "style": "comprehensive style/design DNA analysis",
    "detailed_description": "editorial-quality 5-6 sentence description",
    "colors": ["Pantone-style color names", "color harmony and coordination analysis"],
    "material": "professional material assessment with durability prediction and care requirements",
    "key_features": ["exhaustive list of 10+ distinctive features"],
    "estimated_brand_tier": "detailed tier analysis with market positioning strategy",
    "season_occasion": "complete use case matrix",
    "search_terms": ["10+ optimized search keywords for finding alternatives"],
    "price_estimate": "market-informed pricing with retail vs resale context",
    "financial_analysis": {{
        "estimated_manufacturing_cost": "approximate cost to make",
        "brand_markup_percentage": "estimated markup %",
        "price_trajectory_12mo": "expected price changes",
        "discount_likelihood": "probability of sales/discounts",
        "resale_value_retention": "percentage retained over time"
    }},
    "trend_analysis": {{
        "lifecycle_stage": "rising/peak/declining/timeless",
        "longevity_prediction": "how long this style will remain relevant",
        "trend_influences": "what trends this draws from"
    }},
    "strategic_alternatives": {{
        "better_than_original": "objectively superior quality option",
        "identical_look_less_cost": "30-70% cheaper with same aesthetic",
        "investment_piece": "long-term value option",
        "ultra_budget_gem": "hidden affordable gem",
        "sustainable_ethical": "eco-friendly or ethical alternative"
    }},
    "value_calculations": {{
        "cost_per_wear_projection": "estimated cost per use over 2 years",
        "three_year_value_index": "1-10 score for long-term value",
        "resale_value_estimate": "expected resale price"
    }},
    "wardrobe_integration": {{
        "outfit_suggestions": ["outfit 1", "outfit 2", "outfit 3", "outfit 4", "outfit 5"],
        "complementary_items": ["item 1", "item 2", "item 3"],
        "potential_redundancy_warning": "items you may already own that serve same purpose"
    }},
    "styling_tips": ["5+ expert styling tips"],
    "celebrity_influencer_style": "specific references to who wears similar items",
    "body_type_advice": "who this suits best (if applicable)",
    "care_instructions": "detailed care requirements",
    "versatility_score": "1-10 with explanation",
    "personal_style_match": ["minimalist", "maximalist", "classic", "trendy", "etc."],
    "quality_indicators": "detailed quality assessment with specific observations",
    "similar_brands": ["5+ brands across different price points"],
    "final_verdict": {{
        "recommendation": "buy_original/buy_alternative/wait/skip",
        "alternative_to_buy": "if applicable, specify which",
        "reasoning": "detailed explanation of verdict",
        "confidence_level": "1-10"
    }}
}}

Provide the most comprehensive, actionable product intelligence possible.
This should feel like having a luxury personal shopper + financial analyst in your pocket.
The user should think: "This AI just saved me money and helped me make a smarter decision.\""""

    async def analyze_image(
        self,
        image_path: str,
        tier: str = "free",
        search_mode: str = "alternatives"
    ) -> GeminiAnalysis:
        """
        Analyze an image using Gemini Vision to identify and describe the item.
        Returns detailed analysis based on subscription tier and search mode.

        Args:
            image_path: Local file path to the image
            tier: Subscription tier ('free', 'basic', 'pro', 'unlimited')
            search_mode: Search mode ('exact' for same item, 'alternatives' for similar items)
        """
        prompt = self._get_tier_prompt(tier, search_mode)

        try:
            import os
            import PIL.Image

            # Handle path normalization
            clean_path = image_path.lstrip('/')

            # Load image from disk
            image = PIL.Image.open(clean_path)

            response = self.model.generate_content([prompt, image])

            # Parse JSON from response
            response_text = response.text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            # Parse JSON
            analysis_data = json.loads(response_text)

            # Validate and return as Pydantic model (base fields)
            return GeminiAnalysis(**{
                k: v for k, v in analysis_data.items()
                if k in GeminiAnalysis.model_fields
            })

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to process AI response"
            )
        except Exception as e:
            logger.error(f"Error analyzing image: {type(e).__name__}")
            raise HTTPException(
                status_code=500,
                detail="Error analyzing image"
            )

    def get_tier_features(self, tier: str) -> dict:
        """Get features and limits for a subscription tier."""
        features = {
            "free": {
                "analysis_depth": "basic",
                "max_results": 15,
                "includes_styling_tips": False,
                "includes_trend_analysis": False,
                "includes_celebrity_style": False,
                "includes_alternatives": False,
                "includes_value_analysis": False,
                "includes_buyer_strategy": False,
                "includes_financial_analysis": False,
                "priority_processing": False,
                "description": "Smart Basic Finder - Good results, solid value, fast"
            },
            "basic": {
                "analysis_depth": "enhanced",
                "max_results": 25,
                "includes_styling_tips": False,
                "includes_trend_analysis": False,
                "includes_celebrity_style": False,
                "includes_alternatives": True,
                "includes_value_analysis": True,
                "includes_buyer_strategy": False,
                "includes_financial_analysis": False,
                "priority_processing": False,
                "description": "Value Intelligence - Better comparison logic + quality analysis"
            },
            "pro": {
                "analysis_depth": "premium",
                "max_results": 40,
                "includes_styling_tips": True,
                "includes_trend_analysis": True,
                "includes_celebrity_style": True,
                "includes_alternatives": True,
                "includes_value_analysis": True,
                "includes_buyer_strategy": True,
                "includes_financial_analysis": False,
                "priority_processing": True,
                "description": "Personalized Optimization AI - Strategic advice + use-case optimization"
            },
            "unlimited": {
                "analysis_depth": "ultimate",
                "max_results": 60,
                "includes_styling_tips": True,
                "includes_trend_analysis": True,
                "includes_celebrity_style": True,
                "includes_alternatives": True,
                "includes_value_analysis": True,
                "includes_buyer_strategy": True,
                "includes_financial_analysis": True,
                "priority_processing": True,
                "description": "Elite AI Shopping Agent - Predictive pricing, lifecycle value, wardrobe integration"
            }
        }
        return features.get(tier, features["free"])

    @staticmethod
    def get_ai_disclaimer() -> dict:
        """
        Get AI accuracy disclaimer and tips for better results.
        This should be displayed to users in the app.
        """
        return {
            "disclaimer": {
                "title": "AI Accuracy Notice",
                "message": "AI analysis is not always 100% accurate. Results are estimates based on visual analysis and may vary. Always verify product details, prices, and availability before purchasing.",
                "short": "AI results are estimates and may not be 100% accurate."
            },
            "tips_for_better_results": {
                "title": "Get Better Results",
                "tips": [
                    {
                        "icon": "tag",
                        "title": "Include the Brand",
                        "description": "Photos showing brand logos, labels, or tags help the AI identify products more accurately and find better matches."
                    },
                    {
                        "icon": "camera",
                        "title": "Good Lighting",
                        "description": "Clear, well-lit photos help the AI see details like material, color, and construction quality."
                    },
                    {
                        "icon": "crop",
                        "title": "Focus on the Item",
                        "description": "Crop your photo to show mainly the item you want to find. Less background clutter means better results."
                    },
                    {
                        "icon": "layers",
                        "title": "Show Details",
                        "description": "Multiple angles or close-ups of unique features (stitching, hardware, patterns) improve accuracy."
                    }
                ],
                "pro_tip": "For best results, include any visible brand logos, labels, or tags in your photo. The AI gives significantly more accurate results when it can identify the brand."
            },
            "brand_visibility_note": {
                "title": "Brand Detection",
                "message": "When brand logos or labels are visible in your photo, the AI can provide more accurate product identification, better price estimates, and find closer alternatives across different price points.",
                "benefit": "Photos with visible branding typically get 40% more accurate results."
            }
        }


    async def analyze_text_query(
        self,
        query: str,
        tier: str = "free",
        search_mode: str = "alternatives"
    ) -> GeminiAnalysis:
        """
        Analyze a text query to generate product search terms and analysis.
        Used when user describes an item instead of uploading an image.

        Args:
            query: User's text description of the item they want to find
            tier: Subscription tier ('free', 'basic', 'pro', 'unlimited')
            search_mode: Search mode ('exact' for same item, 'alternatives' for similar items)
        """
        # Build prompt based on tier and search mode
        if search_mode == "exact":
            search_context = """
The user wants to find a SPECIFIC item they're describing.
Focus on generating precise search terms that will find the exact product."""
        else:
            search_context = """
The user wants to find SIMILAR items or ALTERNATIVES to what they're describing.
Focus on generating search terms that will find comparable items across different brands and price points."""

        prompt = f"""You are a product search AI assistant.
The user has described an item they want to find:

"{query}"

{search_context}

Your task is to understand what the user is looking for and generate search-optimized data.

Respond in JSON format:
{{
    "item_type": "specific product type (e.g., 'wireless headphones', 'running shoes', 'leather jacket')",
    "brand": null,
    "style": "style/design category (e.g., 'modern', 'vintage', 'minimalist', 'casual', 'athletic')",
    "detailed_description": "2-3 sentence description of the item based on user's query, filling in typical details",
    "colors": ["likely colors based on description", "or common colors for this type"],
    "material": "likely material type for this product",
    "key_features": ["feature 1", "feature 2", "feature 3", "feature 4", "feature 5"],
    "estimated_brand_tier": "budget/mid-range/premium/luxury - best guess based on description",
    "season_occasion": "when/where this item would be used",
    "search_terms": ["optimized keyword 1", "optimized keyword 2", "optimized keyword 3", "optimized keyword 4", "optimized keyword 5", "optimized keyword 6"],
    "price_estimate": "estimated price range in USD based on typical market prices"
}}

Generate helpful, accurate search terms that will find good product results.
If the user's description is vague, make reasonable assumptions about what they likely want."""

        try:
            response = self.model.generate_content([prompt])

            # Parse JSON from response
            response_text = response.text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            # Parse JSON
            analysis_data = json.loads(response_text)

            # Validate and return as Pydantic model
            return GeminiAnalysis(**{
                k: v for k, v in analysis_data.items()
                if k in GeminiAnalysis.model_fields
            })

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini text response: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to process AI response"
            )
        except Exception as e:
            logger.error(f"Error analyzing text query: {type(e).__name__}")
            raise HTTPException(
                status_code=500,
                detail="Error analyzing text query"
            )


# Singleton instance
gemini_service = GeminiService()
