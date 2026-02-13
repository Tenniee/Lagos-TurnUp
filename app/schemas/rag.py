"""
FastAPI Routes for AI Chat

Add these routes to your FastAPI application.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict

from app.deps.deps import get_db  # Replace with your actual import
from app.crud.user import get_current_user  # Replace with your actual auth import
from app.service.Rag.ai_service import AIService


# ==================== REQUEST/RESPONSE SCHEMAS ====================

class ChatMessage(BaseModel):
    """Single message in conversation."""
    role: str  # "user" or "assistant"
    content: str


'''class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    message: str
    conversation_history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    success: bool
    message: str
    used_rag: Optional[bool] = None
    used_tools: Optional[bool] = None
    sources: Optional[List[str]] = None
    error: Optional[str] = None
'''



class SessionResponse(BaseModel):
    session_id: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    error: Optional[str] = None