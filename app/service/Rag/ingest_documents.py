"""
Document Ingestion Script

Use this script to add your knowledge base documents to the vector database.

Usage:
    python ingest_documents.py
"""
from sqlalchemy.orm import Session
from typing import List
import os

from app.deps.deps import SessionLocal  # Replace with your actual import
from app.models.ai_models import AIDocument
from rag_service import RAGService


def ingest_documents(documents: List[dict], db: Session):
    """
    Ingest documents into the vector database.
    
    Args:
        documents: List of dicts with 'content' and 'source' keys
        db: Database session
    """
    rag_service = RAGService()
    
    print(f"Starting ingestion of {len(documents)} documents...")
    
    for i, doc in enumerate(documents, 1):
        content = doc['content']
        source = doc.get('source', 'Unknown')
        
        print(f"[{i}/{len(documents)}] Processing: {source}")
        
        # Create embedding
        embedding = rag_service.create_embedding(content)
        
        # Create database record
        ai_doc = AIDocument(
            content=content,
            source=source,
            embedding=embedding
        )
        
        db.add(ai_doc)
    
    # Commit all at once
    db.commit()
    print(f"✅ Successfully ingested {len(documents)} documents!")


def load_sample_knowledge_base() -> List[dict]:
    """
    Load your knowledge base documents.
    
    Modify this function to load from:
    - Text files
    - Markdown files
    - Database
    - API
    - Or define inline like below
    
    Returns:
        List of document dicts
    """
    return [
        {
            "content": "ZidePeople is a platform that connects job seekers with employers and helps people discover local events.",
            "source": "Platform Overview"
        },
        {
            "content": "To post an event on ZidePeople, you need to be logged in. Go to the Events section, click 'Create Event', fill in the details including title, description, date, and location, then submit for approval.",
            "source": "How to Post Events"
        },
        {
            "content": "To post a job on ZidePeople, you must have an employer account. Navigate to Jobs > Post New Job, provide the job title, description, requirements, salary range (optional), and location. Jobs are reviewed before going live.",
            "source": "How to Post Jobs"
        },
        {
            "content": "ZidePeople features include: job search and matching, event discovery, company profiles, applicant tracking, event management, and community networking.",
            "source": "Platform Features"
        },
        {
            "content": "Events on ZidePeople can be filtered by date, location, category, and popularity. Featured events appear at the top of the feed. You can RSVP to events if you're logged in.",
            "source": "Event Features"
        },
        {
            "content": "Job matching on ZidePeople uses your profile information, skills, and preferences to recommend relevant job opportunities. Keep your profile updated for better matches.",
            "source": "Job Matching"
        },
        {
            "content": "To create an account on ZidePeople, click Sign Up, choose between Job Seeker or Employer account type, fill in your details, and verify your email address.",
            "source": "Account Creation"
        },
        {
            "content": "ZidePeople's dashboard shows your saved jobs, upcoming events you're attending, recent applications, and personalized recommendations.",
            "source": "Dashboard Features"
        },
        {
            "content": "Companies on ZidePeople can manage multiple job postings, view applicants, schedule interviews, and track hiring pipelines all from their company dashboard.",
            "source": "Employer Features"
        },
        {
            "content": "Privacy on ZidePeople: Your profile visibility can be controlled in settings. You can choose to make your profile public, visible to employers only, or private.",
            "source": "Privacy Settings"
        }
    ]


def clear_existing_documents(db: Session):
    """
    Clear all existing documents from the database.
    Use with caution!
    
    Args:
        db: Database session
    """
    count = db.query(AIDocument).delete()
    db.commit()
    print(f"🗑️  Deleted {count} existing documents")


if __name__ == "__main__":
    # Initialize database session
    db = SessionLocal()
    
    try:
        # Optional: Clear existing documents
        # Uncomment if you want to start fresh
        # clear_existing_documents(db)
        
        # Load your knowledge base
        documents = load_sample_knowledge_base()
        
        # Ingest into vector database
        ingest_documents(documents, db)
        
        print("\n✨ Knowledge base is ready!")
        print("You can now use the AI chat endpoint.")
        
    except Exception as e:
        print(f"❌ Error during ingestion: {e}")
        db.rollback()
    finally:
        db.close()


# ==================== HELPER FUNCTIONS ====================

def ingest_from_text_file(filepath: str, db: Session, source_name: str = None):
    """
    Ingest a single text file.
    
    Args:
        filepath: Path to text file
        db: Database session
        source_name: Name to use as source (defaults to filename)
    """
    if not source_name:
        source_name = os.path.basename(filepath)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    documents = [{"content": content, "source": source_name}]
    ingest_documents(documents, db)


def ingest_from_directory(directory: str, db: Session, file_extension: str = ".txt"):
    """
    Ingest all files from a directory.
    
    Args:
        directory: Path to directory
        db: Database session
        file_extension: File extension to filter (default: .txt)
    """
    documents = []
    
    for filename in os.listdir(directory):
        if filename.endswith(file_extension):
            filepath = os.path.join(directory, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            documents.append({
                "content": content,
                "source": filename
            })
    
    if documents:
        ingest_documents(documents, db)
    else:
        print(f"No files with extension {file_extension} found in {directory}")





























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

from your_app.database import SessionLocal  # ← replace with your import
from ai_models import AIDocument
from rag_service import RAGService


DOCS_DIRECTORY = "./docs_knowledge_base"   # ← point this at your docs folder
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