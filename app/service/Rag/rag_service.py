"""
RAG Service

Handles embedding creation and vector similarity search
against your ai_documents table.
"""
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.service.Rag.openai_client import client, EMBEDDING_MODEL


class RAGService:

    @staticmethod
    def create_embedding(content: str) -> List[float]:
        """Convert text into a vector embedding."""
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=content
        )
        return response.data[0].embedding

    @staticmethod
    def search(query: str, db: Session, limit: int = 5) -> List[Dict]:
        """
        Find the most relevant documents for a query.

        Uses pgvector's <-> (cosine distance) operator.
        Lower distance = more similar.

        Returns list of dicts with content, source, similarity_score.
        """
        query_embedding = RAGService.create_embedding(query)

        rows = db.execute(
            text("""
                SELECT content, source, 1 - (embedding <-> :embedding) AS similarity
                FROM ai_documents
                ORDER BY embedding <-> :embedding
                LIMIT :limit
            """),
            {"embedding": str(query_embedding), "limit": limit}
        ).fetchall()

        return [
            {
                "content":          row[0],
                "source":           row[1],
                "similarity_score": float(row[2])
            }
            for row in rows
        ]

    @staticmethod
    def format_context(documents: List[Dict]) -> str:
        """Format retrieved docs into a string for the system prompt."""
        if not documents:
            return "No relevant documentation found."

        parts = []
        for i, doc in enumerate(documents, 1):
            source = f" (from: {doc['source']})" if doc.get("source") else ""
            parts.append(f"{i}. {doc['content']}{source}")

        return "\n\n".join(parts)


