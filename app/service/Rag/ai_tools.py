"""
AI Tools - Backend Functions the AI Can Call

These are the functions that AI can invoke to get live data from your backend.
You can reuse your existing route functions here.
"""
from typing import Dict, Any, Callable, Optional
from sqlalchemy.orm import Session
from app.models.events import Event  # Replace with your actual imports


class ToolRegistry:
    """
    Registry for AI-callable tools/functions.
    
    This allows the AI to safely call your backend functions with proper
    auth, validation, and error handling.
    """
    
    def __init__(self, db: Session, user: Optional[Any] = None):
        """
        Initialize tool registry with database session and optional user context.
        
        Args:
            db: SQLAlchemy database session
            user: Current authenticated user (if any)
        """
        self.db = db
        self.user = user
    
    # ==================== EVENT TOOLS ====================
    
    def get_latest_events(self) -> Dict:
        """
        Fetch latest approved events.
        
        Returns:
            Dict with list of events
        """
        try:
            # Fetch latest 10 featured/approved events
            events = self.db.query(Event).filter(
                Event.is_featured == True
            ).order_by(Event.created_at.desc()).limit(10).all()
            
            return {
                "success": True,
                "events": [
                    {
                        "id": event.id,
                        "title": event.title,
                        "description": event.description,
                        "date": str(event.date) if hasattr(event, 'date') else None,
                        "location": event.location if hasattr(event, 'location') else None
                    }
                    for event in events
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_event_by_id(self, event_id: int) -> Dict:
        """
        Get details for a specific event.
        
        Args:
            event_id: The ID of the event
            
        Returns:
            Dict with event details
        """
        try:
            event = self.db.query(Event).filter(Event.id == event_id).first()
            if not event:
                return {"success": False, "error": "Event not found"}
            
            return {
                "success": True,
                "event": {
                    "id": event.id,
                    "title": event.title,
                    "description": event.description,
                    "date": str(event.date) if hasattr(event, 'date') else None,
                    "location": event.location if hasattr(event, 'location') else None,
                    "is_featured": event.is_featured
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==================== JOB TOOLS ====================
    
    def get_latest_jobs(self) -> Dict:
        """
        Fetch latest job postings.
        
        Returns:
            Dict with list of jobs
        """
        try:
            jobs = self.db.query(Job).order_by(
                Job.created_at.desc()
            ).limit(10).all()
            
            return {
                "success": True,
                "jobs": [
                    {
                        "id": job.id,
                        "title": job.title,
                        "company": job.company if hasattr(job, 'company') else None,
                        "description": job.description,
                        "location": job.location if hasattr(job, 'location') else None
                    }
                    for job in jobs
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ==================== AUTH HELPER ====================
    
    def require_login_message(self) -> Dict:
        """
        Standard message when user needs to login to perform action.
        
        Returns:
            Dict with login requirement message
        """
        return {
            "success": False,
            "requires_auth": True,
            "message": "You need to be logged in to perform this action. Please log in at /login"
        }
    
    # ==================== TOOL EXECUTOR ====================
    
    def execute_tool(self, tool_name: str, **kwargs) -> Dict:
        """
        Execute a tool by name with given parameters.
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Parameters to pass to the tool
            
        Returns:
            Result from the tool execution
        """
        # Map tool names to methods
        tool_map: Dict[str, Callable] = {
            "get_latest_events": self.get_latest_events,
            "get_event_by_id": self.get_event_by_id,
            "get_latest_jobs": self.get_latest_jobs,
            "require_login": self.require_login_message
        }
        
        tool_func = tool_map.get(tool_name)
        if not tool_func:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        try:
            return tool_func(**kwargs)
        except Exception as e:
            return {"success": False, "error": f"Tool execution failed: {str(e)}"}


# ==================== TOOL DEFINITIONS FOR OPENAI ====================

# These define what tools the AI knows about and can call
AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_latest_events",
            "description": "Fetch the latest approved/featured events from the platform. Use this when users ask about current events, what's happening, or upcoming events.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_event_by_id",
            "description": "Get detailed information about a specific event by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "integer",
                        "description": "The ID of the event to retrieve"
                    }
                },
                "required": ["event_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_latest_jobs",
            "description": "Fetch the latest job postings on the platform. Use this when users ask about available jobs, job opportunities, or what positions are open.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "require_login",
            "description": "Tell the user they need to login to perform an action like posting events, applying to jobs, or accessing protected features.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]
