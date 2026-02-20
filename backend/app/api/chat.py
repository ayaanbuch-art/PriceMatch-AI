"""Chat API endpoints using Gemini."""
import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from typing import List, Optional
import google.generativeai as genai

from ..config import settings
from ..models import User
from ..utils.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Configure Gemini
genai.configure(api_key=settings.GOOGLE_GEMINI_API_KEY)

# Security limits
MAX_HISTORY_LENGTH = 50  # Maximum number of messages in history
MAX_MESSAGE_LENGTH = 5000  # Maximum characters per message
MAX_CONTEXT_LENGTH = 10000  # Maximum characters for context


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v not in ['user', 'assistant']:
            raise ValueError('Role must be "user" or "assistant"')
        return v

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        if len(v) > MAX_MESSAGE_LENGTH:
            raise ValueError(f'Message content must be under {MAX_MESSAGE_LENGTH} characters')
        return v


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []
    context: Optional[str] = None  # Optional context about an image or previous search

    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        if len(v) > MAX_MESSAGE_LENGTH:
            raise ValueError(f'Message must be under {MAX_MESSAGE_LENGTH} characters')
        return v.strip()

    @field_validator('history')
    @classmethod
    def validate_history(cls, v):
        if v and len(v) > MAX_HISTORY_LENGTH:
            raise ValueError(f'History cannot exceed {MAX_HISTORY_LENGTH} messages')
        return v

    @field_validator('context')
    @classmethod
    def validate_context(cls, v):
        if v and len(v) > MAX_CONTEXT_LENGTH:
            raise ValueError(f'Context must be under {MAX_CONTEXT_LENGTH} characters')
        return v


class ChatResponse(BaseModel):
    response: str


# System prompt for the fashion AI assistant
SYSTEM_PROMPT = """You are PriceMatch AI's fashion assistant - a friendly, knowledgeable expert on fashion, style, and shopping. You help users with:

1. **Fashion Advice**: Outfit ideas, style tips, what to wear for occasions, color coordination, seasonal trends
2. **Shopping Help**: Budget recommendations, where to find specific items, quality vs price guidance
3. **Style Questions**: How to dress for body types, fashion terminology, brand comparisons
4. **Wardrobe Tips**: Capsule wardrobes, organizing clothes, mix-and-match strategies
5. **Trend Insights**: Current fashion trends, upcoming styles, celebrity fashion

Guidelines:
- Be friendly, helpful, and encouraging
- Give specific, actionable advice
- Consider budget when giving recommendations
- Be inclusive of all body types, genders, and styles
- If asked about non-fashion topics, politely redirect or give a brief helpful response
- Keep responses concise but informative (2-4 paragraphs max for most questions)
- Use emojis sparingly to keep things friendly

You can also answer general questions, but your expertise is fashion and style."""


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """Send a message to the AI chatbot and get a response."""
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")

        # Build conversation history for context
        conversation_parts = [SYSTEM_PROMPT + "\n\n"]

        # Add image/search context if provided
        if request.context:
            conversation_parts.append(f"[CONTEXT: The user has shared or is asking about the following item:\n{request.context}]\n\n")
            conversation_parts.append("Use this context to provide specific, helpful advice about the item. Reference details like the brand, colors, style, and description when relevant.\n\n")

        # Add previous messages for context
        for msg in request.history[-10:]:  # Keep last 10 messages for context
            if msg.role == "user":
                conversation_parts.append(f"User: {msg.content}\n")
            else:
                conversation_parts.append(f"Assistant: {msg.content}\n")

        # Add the current message
        conversation_parts.append(f"User: {request.message}\n")
        conversation_parts.append("Assistant: ")

        full_prompt = "".join(conversation_parts)

        # Generate response
        response = model.generate_content(full_prompt)

        if response.text:
            return ChatResponse(response=response.text.strip())
        else:
            return ChatResponse(response="I'm sorry, I couldn't generate a response. Please try again.")

    except Exception as e:
        # Generate error ID for tracking
        error_id = str(uuid.uuid4())[:8]
        logger.error(f"Chat error [{error_id}]: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate response. Error ID: {error_id}"
        )
