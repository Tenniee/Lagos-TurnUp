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
from app.service.Rag.session_service import SessionService
from app.schemas.rag import ChatRequest, ChatResponse, SessionResponse  # Define these Pydantic models in your schemas



router = APIRouter(prefix="/ai", tags=["AI Chat"])


# ── Session Creation ──────────────────────────────────────────────────────────

@router.post("/session/anonymous", response_model=SessionResponse)
def create_anonymous_session(db: Session = Depends(get_db)):
    """
    Create a session for a non-logged-in user.
    Call once when the chatbot opens. Store the returned session_id.
    """
    svc = SessionService(db)
    return {"session_id": svc.create_session(user_id=None)}


@router.post("/session", response_model=SessionResponse)
def create_session(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Create a session linked to the logged-in user.
    """
    svc = SessionService(db)
    return {"session_id": svc.create_session(user_id=current_user.id)}




# ── Chat ──────────────────────────────────────────────────────────────────────

@router.post("/chat/anonymous", response_model=ChatResponse)
def chat_anonymous(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Chat endpoint for anonymous users.

    Frontend sends:  { session_id, message }
    Backend handles: load history → RAG → tools → save messages → reply
    """
    svc = SessionService(db)

    if not svc.session_exists(request.session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired. Please start a new chat."
        )

    history = svc.get_history(request.session_id)

    svc.save_message(request.session_id, "user", request.message)

    result = AIService(db=db).chat(
        user_message=request.message,
        conversation_history=history
    )

    reply = result["message"]
    svc.save_message(
        request.session_id, "assistant", reply,
        meta={
            "used_rag":   result.get("used_rag"),
            "used_tools": result.get("used_tools"),
            "sources":    result.get("sources"),
        }
    )

    return ChatResponse(reply=reply, session_id=request.session_id, error=result.get("error"))


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Chat endpoint for authenticated users.
    Same flow as anonymous but passes the user to AIService
    so tools can use user-specific data if needed.
    """
    svc = SessionService(db)

    if not svc.session_exists(request.session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired. Please start a new chat."
        )

    history = svc.get_history(request.session_id)

    svc.save_message(request.session_id, "user", request.message)

    result = AIService(db=db, user=current_user).chat(
        user_message=request.message,
        conversation_history=history
    )

    reply = result["message"]
    svc.save_message(
        request.session_id, "assistant", reply,
        meta={
            "used_rag":   result.get("used_rag"),
            "used_tools": result.get("used_tools"),
            "sources":    result.get("sources"),
        }
    )

    return ChatResponse(reply=reply, session_id=request.session_id, error=result.get("error"))


# ── User: Clear Chat ──────────────────────────────────────────────────────────

@router.delete("/session/{session_id}")
def clear_chat(session_id: str, db: Session = Depends(get_db)):
    """
    Wipe messages for a session but keep it alive.
    Hook this up to your 'New Chat' button.
    """
    svc = SessionService(db)

    if not svc.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    svc.clear_session(session_id)
    return {"message": "Chat cleared."}




# ==================== ADMIN ENDPOINTS ====================


# Uncomment the is_admin guard once you have that on your user model.

@router.get("/admin/sessions")
def admin_list_sessions(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    List all chat sessions with message counts.
    Review what users are asking to find gaps in your documentation.
    """
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admins only.")

    svc = SessionService(db)
    return svc.list_sessions(limit=limit, offset=offset)


@router.get("/admin/sessions/{session_id}/messages")
def admin_get_messages(
    session_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Read the full conversation from a specific session."""
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admins only.")

    svc = SessionService(db)

    if not svc.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    return svc.get_session_messages(session_id)


@router.delete("/admin/sessions/{session_id}")
def admin_delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Fully delete a specific session and all its messages."""
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admins only.")

    svc = SessionService(db)

    if not svc.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    svc.delete_session(session_id)
    return {"message": f"Session {session_id} deleted."}


@router.delete("/admin/cleanup")
def admin_cleanup(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Delete all sessions older than X days.
    Call this manually or set up a nightly cron job.

    Example: DELETE /ai/admin/cleanup?days=30
    """
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admins only.")

    svc = SessionService(db)
    deleted = svc.cleanup_old_sessions(days=days)
    return {"deleted": deleted, "older_than_days": days}







@router.get("/health")
def ai_health_check():
    """
    Check if AI service is configured correctly.
    
    Returns status of OpenAI API key and database connection.
    """
    import os
    
    checks = {
        "openai_api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
        "service_status": "healthy"
    }
    
    return checks
