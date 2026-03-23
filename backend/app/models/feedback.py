"""Search feedback model for AI improvement."""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class SearchFeedback(Base):
    """
    Stores user feedback on search results to improve AI accuracy.

    This data is used to:
    1. Identify common AI mistakes (e.g., misidentifying baggy vs skinny jeans)
    2. Improve Gemini prompts based on real user corrections
    3. Track accuracy over time
    """

    __tablename__ = "search_feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    search_id = Column(Integer, ForeignKey("search_history.id"), nullable=True)

    # Feedback data
    is_accurate = Column(Boolean, nullable=False)  # True = results were good, False = results were wrong
    feedback_type = Column(String, nullable=True)  # 'wrong_item', 'wrong_color', 'wrong_fit', 'wrong_brand', 'other'
    feedback_text = Column(Text, nullable=True)  # User's description of what was wrong

    # What the AI detected vs what user says is correct
    ai_detected_item = Column(String, nullable=True)  # What AI thought it was
    correct_item = Column(String, nullable=True)  # What user says it actually is
    ai_detected_fit = Column(String, nullable=True)  # What AI detected for fit
    correct_fit = Column(String, nullable=True)  # What user says the fit is
    ai_detected_brand = Column(String, nullable=True)
    correct_brand = Column(String, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", backref="feedback")


class PremiumPreviewUsage(Base):
    """
    Tracks weekly premium preview usage for free users.

    Free users get 3 premium searches per week to experience the value.
    """

    __tablename__ = "premium_preview_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    # Weekly tracking
    previews_used_this_week = Column(Integer, default=0)
    week_start_date = Column(DateTime(timezone=True), nullable=True)  # Start of current tracking week

    # Lifetime stats
    total_previews_used = Column(Integer, default=0)

    # Timestamps
    last_preview_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="premium_preview")

    # Constants
    MAX_WEEKLY_PREVIEWS = 3

    def get_remaining_previews(self) -> int:
        """Get remaining premium previews for this week."""
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)

        # Reset if it's a new week (weeks start on Monday)
        if self.week_start_date is None:
            self.week_start_date = now - timedelta(days=now.weekday())
            self.previews_used_this_week = 0
        else:
            # Check if we're in a new week
            current_week_start = now - timedelta(days=now.weekday())
            current_week_start = current_week_start.replace(hour=0, minute=0, second=0, microsecond=0)

            if self.week_start_date.date() < current_week_start.date():
                # New week - reset counter
                self.week_start_date = current_week_start
                self.previews_used_this_week = 0

        return max(0, self.MAX_WEEKLY_PREVIEWS - (self.previews_used_this_week or 0))

    def can_use_preview(self) -> bool:
        """Check if user can use a premium preview."""
        return self.get_remaining_previews() > 0

    def use_preview(self) -> bool:
        """Use a premium preview. Returns True if successful."""
        from datetime import datetime, timezone

        if not self.can_use_preview():
            return False

        self.previews_used_this_week = (self.previews_used_this_week or 0) + 1
        self.total_previews_used = (self.total_previews_used or 0) + 1
        self.last_preview_at = datetime.now(timezone.utc)
        return True
