"""
Session Service

Manages chat sessions and message history in PostgreSQL.
Frontend only ever needs to store and send the session_id.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.ai_models import ChatSession, ChatMessage


class SessionService:

    def __init__(self, db: Session):
        self.db = db

    # ── Session Management ────────────────────────────────────────────────────

    def create_session(self, user_id: Optional[int] = None) -> str:
        """
        Create a new chat session.

        Args:
            user_id: Pass the logged-in user's ID, or None for anonymous.

        Returns:
            session_id (UUID string) for the frontend to store.
        """
        session = ChatSession(user_id=user_id)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session.id

    def session_exists(self, session_id: str) -> bool:
        """Return True if the session ID exists in the DB."""
        return (
            self.db.query(ChatSession)
            .filter(ChatSession.id == session_id)
            .first()
        ) is not None

    def clear_session(self, session_id: str):
        """
        Delete all messages in a session but keep the session itself.
        Use this for a 'New Chat' button on the frontend.
        """
        self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).delete()
        self.db.commit()

    def delete_session(self, session_id: str):
        """
        Fully delete a session.
        Messages are removed automatically via CASCADE.
        """
        self.db.query(ChatSession).filter(
            ChatSession.id == session_id
        ).delete()
        self.db.commit()

    # ── Message Management ────────────────────────────────────────────────────

    def get_history(self, session_id: str, limit: int = 20) -> List[Dict]:
        """
        Load the last N messages for a session in OpenAI format.

        Args:
            session_id: The session to load
            limit: Max messages to return (keeps token count manageable)

        Returns:
            [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
        """
        messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )

        # Reverse so they're in chronological order for OpenAI
        return [
            {"role": m.role, "content": m.content}
            for m in reversed(messages)
        ]

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        meta: Optional[Dict] = None
    ):
        """
        Save a message to the session.

        Args:
            session_id: Session to save to
            role:       "user" or "assistant"
            content:    Message text
            meta:       Optional dict (used_rag, used_tools, sources, etc.)
        """
        self.db.add(ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            meta=meta
        ))
        self.db.commit()

    # ── Admin / Cleanup ───────────────────────────────────────────────────────

    def cleanup_old_sessions(self, days: int = 30) -> int:
        """
        Delete sessions older than X days.
        Messages are removed automatically via CASCADE.

        Call this from a scheduled task (cron, APScheduler) to keep the DB clean.

        Args:
            days: Sessions older than this are deleted (default 30)

        Returns:
            Number of sessions deleted
        """
        cutoff  = datetime.now() - timedelta(days=days)
        deleted = (
            self.db.query(ChatSession)
            .filter(ChatSession.created_at < cutoff)
            .delete()
        )
        self.db.commit()
        return deleted

    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """
        List all sessions with message counts.
        Useful for reviewing what users are asking the AI.
        """
        rows = (
            self.db.query(
                ChatSession.id,
                ChatSession.user_id,
                ChatSession.created_at,
                func.count(ChatMessage.id).label("message_count")
            )
            .outerjoin(ChatMessage, ChatMessage.session_id == ChatSession.id)
            .group_by(ChatSession.id)
            .order_by(ChatSession.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return [
            {
                "session_id":    r.id,
                "user_id":       r.user_id,
                "created_at":    str(r.created_at),
                "message_count": r.message_count,
            }
            for r in rows
        ]

    def get_session_messages(self, session_id: str) -> List[Dict]:
        """
        Get the full conversation for a session (for admin review).
        """
        messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )

        return [
            {
                "role":       m.role,
                "content":    m.content,
                "created_at": str(m.created_at),
            }
            for m in messages
        ]
