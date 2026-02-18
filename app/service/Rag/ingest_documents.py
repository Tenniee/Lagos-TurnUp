"""
Document Ingestion Script

Reads your text files and loads them into the ai_documents table
as vector embeddings for RAG search.

Usage:
    # Ingest all .txt files from docs/ folder
    python ingest_docs.py

    # Clear existing and re-ingest
    python ingest_docs.py --clear
"""
import os
import argparse
from sqlalchemy.orm import Session

from app.core.database import SessionLocal  # ← replace with your import
from app.models.ai_models import AIDocument
from app.service.Rag.rag_service import RAGService


DOCS_DIRECTORY = "app\service\Rag\doc"   # ← point this at your docs folder
CHUNK_SIZE     = 1000                      # characters per chunk
CHUNK_OVERLAP  = 150                       # overlap between chunks


def chunk_text(text: str) -> list[str]:
    """
    Split text into overlapping chunks so long files get
    indexed properly and retrieval stays precise.
    """
    if len(text) <= CHUNK_SIZE:
        return [text.strip()]

    chunks = []
    start  = 0

    while start < len(text):
        end   = start + CHUNK_SIZE
        chunk = text[start:end]

        # Try to break at a sentence boundary
        if end < len(text):
            break_at = max(chunk.rfind(". ", -150), chunk.rfind("\n", -150))
            if break_at > 0:
                chunk = chunk[:break_at + 1]
                end   = start + break_at + 1

        if chunk.strip():
            chunks.append(chunk.strip())

        start = end - CHUNK_OVERLAP

    return chunks


def ingest_directory(directory: str, db: Session, clear: bool = False):
    """Ingest all .txt files from a directory."""
    if clear:
        deleted = db.query(AIDocument).delete()
        db.commit()
        print(f"🗑️  Cleared {deleted} existing documents\n")

    files = [f for f in os.listdir(directory) if f.endswith(".txt") or f.endswith(".md")]

    if not files:
        print(f"No .txt or .md files found in {directory}")
        return

    rag   = RAGService()
    total = 0

    print(f"Found {len(files)} files\n")

    for filename in sorted(files):
        filepath    = os.path.join(directory, filename)
        source_name = filename.replace(".txt", "").replace(".md", "").replace("-", " ").title()

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        chunks = chunk_text(content)
        print(f"  {filename}  →  {len(chunks)} chunk(s)")

        for i, chunk in enumerate(chunks):
            embedding = rag.create_embedding(chunk)

            db.add(AIDocument(
                content   = chunk,
                embedding = embedding,
                source    = source_name if len(chunks) == 1 else f"{source_name} ({i+1}/{len(chunks)})"
            ))
            total += 1

    db.commit()
    print(f"\n✅ Ingested {total} chunks from {len(files)} files")
    print("Your knowledge base is ready.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true", help="Clear existing docs before ingesting")
    parser.add_argument("--dir",   type=str, default=DOCS_DIRECTORY, help="Directory to ingest from")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        ingest_directory(args.dir, db, clear=args.clear)
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()