"""
OpenAI Client Configuration

Centralized OpenAI client for reuse across your application.
"""
from openai import OpenAI
import os

# Initialize OpenAI client (reads from OPENAI_API_KEY environment variable)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Embedding model to use (consistent across ingestion and retrieval)
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

# Chat model to use
CHAT_MODEL = "gpt-4o"  # or "gpt-4o-mini" for faster/cheaper responses