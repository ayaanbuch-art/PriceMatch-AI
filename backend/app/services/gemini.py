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

ACT AS: A professional fashion stylist and computer vision expert.

CRITICAL ANALYSIS REQUIREMENTS:
- Brand identification (look for logos, labels, tags, distinctive design elements)
- Specific model/product name if visible
- Unique identifying features that distinguish this from similar items
- Use industry-standard fashion terminology for precise matching

Look VERY carefully for any visible brand logos, labels, tags, text, packaging, or distinctive brand design elements.

FASHION-SPECIFIC DETAILS TO IDENTIFY:
- Exact item category (e.g., 'Midi Dress', 'Chelsea Boot', 'Cropped Hoodie', 'Wide-leg Trousers')
- Primary color with specific shade (e.g., 'Emerald Green', 'Burgundy', 'Cream White')
- Material/texture description (e.g., 'Ribbed knit', 'Distressed denim', 'Satin-finish', 'Genuine leather')
- Necklines, sleeve types, closures, hardware details
- Fit/silhouette (e.g., 'Oversized', 'Slim-fit', 'A-line', 'Relaxed', 'Tailored')

SEARCH TERM PRIORITY: Generate search terms that will find the EXACT product:
- Include brand name + model if known
- Use specific fashion terminology (e.g., "Nike Air Force 1 '07 white leather low-top sneakers")
- Include unique design elements in search terms
"""
        else:
            search_context = """
SEARCH MODE: FIND ALTERNATIVES
The user wants to find SIMILAR items or CHEAPER ALTERNATIVES.

ACT AS: A professional fashion stylist and computer vision expert optimizing for e-commerce search accuracy.

CRITICAL: Provide the SAME level of detail as exact match mode - detailed analysis enables better alternative matching.

FASHION-SPECIFIC DETAILS TO IDENTIFY:
- Exact item category (e.g., 'Midi Dress', 'Chelsea Boot', 'Cropped Hoodie', 'Wide-leg Trousers')
- Primary color with specific shade (e.g., 'Emerald Green', 'Burgundy', 'Cream White')
- Material/texture description (e.g., 'Ribbed knit', 'Distressed denim', 'Satin-finish', 'Genuine leather')
- Necklines, sleeve types, closures, hardware, embellishments
- Fit/silhouette (e.g., 'Oversized', 'Slim-fit', 'A-line', 'Relaxed', 'Tailored')
- Style keywords (e.g., 'Boho', 'Minimalist', 'Streetwear', 'Y2K', 'Cottagecore', 'Old Money')

Look carefully for any visible brand logos, labels, or distinctive design elements - this helps find alternatives at different price points.

SEARCH TERM PRIORITY: Generate a refined 5-8 word search string for accurate retail results:
- Focus on descriptive fashion terms (e.g., "oversized cream cable knit fisherman sweater")
- Include style descriptors and silhouette details
- Use industry-standard fashion terminology to match retail catalogs
"""

        # =============================================================================
        # FREE PLAN – "Smart Basic Finder"
        # Goal: Good results. Solid value. Fast.
        # Positioning: Useful and reliable, but not deeply personalized.
        # =============================================================================
        if tier == "free":
            return f"""You are a professional fashion stylist and computer vision expert.
The user has uploaded an image of a fashion item.

{search_context}

Your tasks:
1. Identify the EXACT item category using fashion terminology (e.g., 'Midi Wrap Dress', 'Chelsea Boots', 'Cropped Puffer Jacket').
2. Describe primary color with SPECIFIC shade (e.g., 'Emerald Green', 'Dusty Rose', 'Charcoal Gray').
3. Identify material/texture (e.g., 'Ribbed knit', 'Distressed denim', 'Satin-finish', 'Suede').
4. List 3-5 distinct key features (necklines, sleeve types, closures, hardware, embellishments).
5. Describe fit/silhouette (e.g., 'Oversized', 'Slim-fit', 'A-line', 'Relaxed', 'Tailored').
6. Generate style keywords for search optimization.
7. Create a refined 5-8 word search query string for accurate retail results.

IMPORTANT: Focus ONLY on the main garment or accessory in the foreground. Ignore background clutter.

Respond in JSON format:
{{
    "item_type": "exact fashion category (e.g., 'Midi Wrap Dress', 'Chelsea Ankle Boots', 'Cropped Puffer Jacket')",
    "brand": "brand name if visible, or null if unknown",
    "style": "style aesthetic (e.g., 'Minimalist', 'Streetwear', 'Boho', 'Y2K', 'Old Money', 'Cottagecore')",
    "detailed_description": "2-3 sentence item summary using fashion terminology",
    "colors": ["primary color with shade (e.g., 'Emerald Green')", "secondary color if present"],
    "material": "material/texture description (e.g., 'Ribbed cotton knit', 'Distressed denim', 'Genuine leather')",
    "fit_silhouette": "fit description (e.g., 'Oversized relaxed fit', 'Slim-fit tailored', 'A-line flared')",
    "key_features": ["neckline/collar type", "sleeve type", "closure type", "hardware/embellishments", "unique details"],
    "estimated_brand_tier": "luxury/premium/mid-range/budget",
    "season_occasion": "when/where to wear this",
    "search_terms": ["optimized keyword 1", "keyword 2", "keyword 3", "keyword 4", "keyword 5"],
    "search_query": "refined 5-8 word search string for best retail results",
    "price_estimate": "estimated price range in USD",
    "why_good_value": "brief explanation of what makes alternatives good value"
}}

Use industry-standard fashion terminology to ensure better matches with retail catalogs.
Provide accurate, helpful information for finding {"this exact item" if search_mode == "exact" else "similar items at better prices"}."""

        # =============================================================================
        # $4.99 PLAN – "Value Intelligence"
        # Upgrade Difference: Better comparison logic + quality analysis.
        # =============================================================================
        elif tier == "basic":
            return f"""You are an advanced fashion intelligence AI trained as a professional stylist with expertise in price-to-quality analysis.
The user uploaded an image of a fashion item.

{search_context}

Your tasks:
1. Identify the item using PRECISE fashion terminology:
   - Exact category (e.g., 'High-waisted Wide-leg Trousers', 'Oversized Boyfriend Blazer')
   - Era/trend influence (e.g., '90s minimalist', 'Y2K', 'Quiet Luxury')
   - Construction details (seams, stitching quality, hardware)
2. Analyze material with fashion expertise:
   - Fabric type (e.g., 'Heavyweight cotton twill', 'Silk crepe de chine', 'Wool-blend bouclé')
   - Texture description (e.g., 'Ribbed', 'Distressed', 'Garment-dyed')
3. Reverse-engineer pricing factors (brand markup, materials, trend factor).
4. Find 8–12 alternatives matching aesthetic ≥ 85% similarity.
5. Calculate Value Score (1–10) based on material quality and price fairness.

IMPORTANT: Focus ONLY on the main garment in the foreground. Use industry-standard fashion terminology.

Respond in JSON format:
{{
    "item_type": "precise fashion category (e.g., 'High-waisted Wide-leg Pleated Trousers')",
    "brand": "brand name if visible, or null if unknown",
    "style": "style aesthetic with era influence (e.g., 'Minimalist 90s-inspired', 'Y2K streetwear')",
    "detailed_description": "comprehensive 3-4 sentence description using fashion terminology",
    "colors": ["primary color with exact shade (e.g., 'Dusty Mauve')", "secondary colors", "accent colors"],
    "material": "detailed fabric analysis (e.g., 'Midweight ribbed cotton jersey with slight stretch')",
    "fit_silhouette": "precise fit description (e.g., 'Relaxed oversized fit with dropped shoulders')",
    "key_features": ["neckline type", "sleeve style", "closure details", "hardware", "embellishments", "hem details"],
    "estimated_brand_tier": "luxury/premium/mid-range/budget with reasoning",
    "season_occasion": "detailed styling occasions",
    "search_terms": ["optimized fashion keyword 1", "keyword 2", "keyword 3", "keyword 4", "keyword 5", "keyword 6", "keyword 7"],
    "search_query": "refined 6-10 word search string using fashion terminology",
    "price_estimate": "estimated price range with confidence level",
    "why_it_costs_this": "explanation of price factors (brand markup, materials, design, trend)",
    "value_score_factors": {{
        "material_quality": "1-10",
        "construction_quality": "1-10",
        "price_fairness": "1-10",
        "brand_markup_level": "low/medium/high",
        "overall_value_score": "1-10"
    }},
    "best_overall_pick": "description of best overall alternative with style match",
    "best_budget_pick": "description of best budget alternative",
    "what_you_sacrifice": "quality/style differences in alternatives",
    "similar_brands": ["brand 1", "brand 2", "brand 3", "brand 4"]
}}

Provide insightful fashion analysis that helps users find better alternatives."""

        # =============================================================================
        # $9.99 PLAN – "Personalized Optimization AI"
        # Upgrade Difference: Personalization + strategic advice + use-case optimization.
        # =============================================================================
        elif tier == "pro":
            return f"""You are an elite fashion consultant AI combining expertise as a professional stylist, fashion buyer, and consumer optimization specialist.
The user uploaded an image and may have provided preferences (budget, brands they like, quality priorities, sustainability, etc.).

{search_context}

Your tasks:
1. Perform EXPERT fashion analysis:
   - Precise item category using industry terminology (e.g., 'Double-breasted Wool-blend Overcoat')
   - Construction quality (seams, stitching, finishing details)
   - Fabric identification with weight/hand description
   - Target demographic and price psychology
2. Style DNA analysis:
   - Aesthetic category (e.g., 'Quiet Luxury', 'Coastal Grandmother', 'Dark Academia')
   - Era/trend influences
   - Designer references if applicable
3. Determine price verdict (overpriced/fair/underpriced) with fashion market context.
4. Generate 10–15 alternatives segmented by purpose.
5. Provide Smart Buyer Strategy with seasonal timing.

IMPORTANT: Focus ONLY on the main garment. Use precise fashion terminology matching retail catalogs.

Respond in JSON format:
{{
    "item_type": "precise fashion terminology (e.g., 'Double-breasted Wool-blend Midi Overcoat')",
    "brand": "brand identification with confidence level (e.g., 'Max Mara (85% confident)')",
    "style": "style DNA analysis (e.g., 'Quiet Luxury minimalism with 90s Carolyn Bessette influence')",
    "detailed_description": "thorough 4-5 sentence editorial description using fashion terminology",
    "colors": ["exact shade (e.g., 'Camel', 'Ecru', 'Slate Blue')", "color harmony analysis"],
    "material": "expert fabric analysis (e.g., 'Heavyweight wool-cashmere blend with satin lining, approx 400gsm')",
    "fit_silhouette": "precise fit description (e.g., 'Relaxed tailored fit with structured shoulders and A-line skirt')",
    "key_features": ["lapel style", "button details", "pocket types", "lining", "shoulder construction", "hem finish", "sleeve details", "back details"],
    "estimated_brand_tier": "detailed tier analysis with market positioning",
    "season_occasion": "comprehensive styling guide with occasions",
    "search_terms": ["8+ optimized fashion keywords for retail search"],
    "search_query": "refined 8-12 word professional search string",
    "price_estimate": "precise price range with market context",
    "price_verdict": "overpriced/fairly_priced/underpriced with detailed fashion market explanation",
    "construction_quality": "detailed assessment (stitching, seams, hardware, finishing)",
    "target_demographic": "who this item is designed for with style persona",
    "alternatives_segmented": {{
        "best_overall_value": "specific alternative with brand/style match",
        "premium_alternative": "higher quality option at similar price",
        "budget_steal": "great dupe under $100",
        "trendy_alternative": "on-trend interpretation",
        "durability_pick": "investment piece for 5+ years"
    }},
    "smart_buyer_strategy": {{
        "best_time_to_buy": "seasonal timing (e.g., 'End of season sales in January')",
        "where_to_buy": "specific retailers (e.g., 'SSENSE, NET-A-PORTER, Nordstrom')",
        "wait_for_discount": "true/false with reasoning",
        "resale_tip": "if applicable, resale market advice"
    }},
    "styling_tips": ["5 specific outfit pairing tips"],
    "wardrobe_pairings": ["complementary item 1", "item 2", "item 3", "item 4"],
    "trend_context": "current trend relevance with longevity prediction (e.g., 'Quiet Luxury trending through 2027')",
    "celebrity_style_reference": "who wears similar (e.g., 'Sofia Richie, Rosie Huntington-Whiteley aesthetic')",
    "similar_brands": ["brand 1", "brand 2", "brand 3", "brand 4", "brand 5"],
    "final_recommendation": "clear verdict on what to do"
}}

Think like a personal stylist + fashion buyer. Provide advice that makes users feel like they have insider fashion knowledge."""

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
