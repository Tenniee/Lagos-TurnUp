"""
AI Service

Orchestrates the full pipeline:
  1. Search RAG docs for context
  2. Send to OpenAI with tools available
  3. If AI calls a tool → execute it → send result back to OpenAI
  4. Return final answer
"""
import json
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

from app.service.Rag.openai_client import client, CHAT_MODEL
from app.service.Rag.rag_service import RAGService
from app.service.Rag.ai_tools import ToolRegistry, AVAILABLE_TOOLS


class AIService:

    def __init__(self, db: Session, user: Optional[Any] = None):
        self.db            = db
        self.user          = user
        self.rag           = RAGService()
        self.tool_registry = ToolRegistry(db, user)

    def chat(self, user_message: str, conversation_history: Optional[List[Dict]] = None) -> Dict:
        """
        Main entry point. Called by the FastAPI route on every message.

        Args:
            user_message:         The user's latest message
            conversation_history: Previous messages loaded from DB/session

        Returns:
            {
                "success":    True/False,
                "message":    "AI reply text",
                "used_rag":   True/False,
                "used_tools": True/False,
                "sources":    ["source name", ...],
                "error":      "error string or None"
            }
        """
        try:
            # Step 1 - RAG: find relevant docs
            docs    = self.rag.search(user_message, self.db, limit=5)
            context = self.rag.format_context(docs)

            # Step 2 - Build messages array for OpenAI
            messages = self._build_messages(context, user_message, conversation_history)

            # Step 3 - First OpenAI call (AI may decide to call a tool)
            response        = client.chat.completions.create(
                model=CHAT_MODEL,
                messages=messages,
                tools=AVAILABLE_TOOLS,
                tool_choice="auto"
            )
            assistant_msg = response.choices[0].message

            # Step 4 - Handle tool calls if the AI requested any
            if assistant_msg.tool_calls:
                messages = self._append_tool_results(messages, assistant_msg)

                # Step 5 - Second OpenAI call with tool results included
                final   = client.chat.completions.create(
                    model=CHAT_MODEL,
                    messages=messages
                )
                reply = final.choices[0].message.content
            else:
                reply = assistant_msg.content

            return {
                "success":    True,
                "message":    reply,
                "used_rag":   len(docs) > 0,
                "used_tools": bool(assistant_msg.tool_calls),
                "sources":    [d["source"] for d in docs if d.get("source")],
                "error":      None,
            }

        except Exception as ex:
            return {
                "success":    False,
                "message":    "I'm having trouble right now. Please try again.",
                "used_rag":   None,
                "used_tools": None,
                "sources":    None,
                "error":      str(ex),
            }

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _build_messages(
        self,
        context: str,
        user_message: str,
        history: Optional[List[Dict]]
    ) -> List[Dict]:
        """Assemble the full messages list for OpenAI."""
        system_prompt = f"""You are a helpful assistant for TurnUp Lagos, a platform that connects people with jobs and events.

Your responsibilities:
- Answer questions about how the platform works using the documentation context below
- Fetch live data (events, jobs) using the tools available to you
- Guide users who want to post events or jobs to log in first
- Be concise and accurate

Documentation context:
{context}

Guidelines:
- Use tools when users ask for live data (events, jobs)
- Use the require_login tool when users want to post, apply, or do anything that needs an account
- If you don't know something, say so honestly
"""
        messages = [{"role": "system", "content": system_prompt}]

        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": user_message})
        return messages

    def _append_tool_results(self, messages: List[Dict], assistant_msg) -> List[Dict]:
        """Execute tool calls and append results to the messages list."""

        # Add the assistant's tool_call message
        messages.append({
            "role":       "assistant",
            "content":    assistant_msg.content,
            "tool_calls": [
                {
                    "id":       tc.id,
                    "type":     "function",
                    "function": {
                        "name":      tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in assistant_msg.tool_calls
            ]
        })

        # Execute each tool and append its result
        for tc in assistant_msg.tool_calls:
            try:
                args   = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args   = {}

            result = self.tool_registry.execute_tool(tc.function.name, **args)

            messages.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      json.dumps(result)
            })

        return messages