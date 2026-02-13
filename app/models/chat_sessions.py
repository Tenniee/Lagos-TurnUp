"""
Conversation Session Models

Stores chat sessions and message history in your Postgres DB.
No need to send history from the frontend anymore.
"""
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base  # Replace with your actual Base import


class ChatSession(Base):
    """
    Represents a single conversation session.
    
    Each user (or anonymous visitor) gets a session ID.
    The frontend only needs to store and send this ID.
    """
    __tablename__ = "chat_sessions"

    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null = anonymous
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to messages
    messages = relationship("ChatMessage", back_populates="session", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    """
    A single message in a conversation session.
    
    Stores both user messages and AI responses.
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Text, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(Text, nullable=False)     # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Optional metadata (which tools were used, etc.)
    meta = Column(JSON, nullable=True)

    # Relationship back to session
    session = relationship("ChatSession", back_populates="messages")
