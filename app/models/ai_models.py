"""
AI Document Model for RAG System

This model stores your knowledge base documents with their embeddings
for semantic search using pgvector.
"""
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base  # Replace with your actual Base import
import uuid



class AIDocument(Base):
    """
    Stores documents with vector embeddings for RAG retrieval.
    
    Attributes:
        id: Primary key
        content: The actual text content of the document
        embedding: Vector embedding (1536 dimensions for text-embedding-3-small)
        source: Where this content came from (e.g., "FAQ", "How-to Guide")
        created_at: Timestamp when document was added
    """
    __tablename__ = "ai_documents"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=False)  # OpenAI embedding dimension
    source = Column(Text, nullable=True)  # Optional: track where content came from
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<AIDocument(id={self.id}, source={self.source})>"

class ChatSession(Base):
    """One conversation thread. Anonymous if user_id is None."""
    __tablename__ = "chat_sessions"

    id         = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = Column(Integer, ForeignKey("sub_admins.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    messages   = relationship(
        "ChatMessage",
        back_populates="session",
        order_by="ChatMessage.created_at",
        cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    """A single user or assistant message inside a session."""
    __tablename__ = "chat_messages"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(Text, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role       = Column(Text, nullable=False)   # "user" or "assistant"
    content    = Column(Text, nullable=False)
    meta       = Column(JSON, nullable=True)    # used_rag, used_tools, sources
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session    = relationship("ChatSession", back_populates="messages")
