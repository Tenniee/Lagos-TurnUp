"""
AI Tools - Backend Functions the AI Can Call

These are the functions that AI can invoke to get live data from your backend.
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
        Fetch all latest events.
        
        Returns:
            Dict with list of events
        """
        try:
            # Fetch all events, ordered by most recent (increased to 20)
            events = self.db.query(Event).order_by(Event.created_at.desc()).limit(20).all()
            
            return {
                "success": True,
                "events": [
                    {
                        "id": event.id,
                        "title": event.event_name,
                        "description": event.event_description,
                        "location": event.venue,
                        "date": str(event.date) if hasattr(event, 'date') else None,
                        "state": event.state if hasattr(event, 'state') else None,
                        "is_featured": event.is_featured if hasattr(event, 'is_featured') else False
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
                    "title": event.event_name,
                    "description": event.event_description,
                    "location": event.venue,
                    "date": str(event.date) if hasattr(event, 'date') else None,
                    "state": event.state if hasattr(event, 'state') else None,
                    "is_featured": event.is_featured if hasattr(event, 'is_featured') else False
                }
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
            "message": "You need to be logged in to perform this action. Please log in or create an account."
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
            "description": "Fetch the latest events from TurnUp Lagos. Use this when users ask about events, what's happening, upcoming events, or event listings.",
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
            "name": "require_login",
            "description": "Tell the user they need to login to perform an action like posting events or accessing protected features. TurnUp Lagos does NOT have job postings - it's only for events.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]