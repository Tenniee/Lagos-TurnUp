"""
Alembic Migration: Add pgvector and ai_documents table

This migration:
1. Enables the pgvector extension
2. Creates the ai_documents table with vector column

If you're using Alembic, save this as a migration file.
If not, run the SQL directly in your database.

Revision ID: add_pgvector_and_ai_docs
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


def upgrade():
    """Apply the migration."""
    
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create ai_documents table
    op.create_table(
        'ai_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('source', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on id for faster lookups
    op.create_index(op.f('ix_ai_documents_id'), 'ai_documents', ['id'], unique=False)
    
    # Create index for vector similarity search (HNSW index for better performance)
    # This speeds up the <-> similarity operator
    op.execute(
        'CREATE INDEX ON ai_documents USING hnsw (embedding vector_cosine_ops)'
    )


def downgrade():
    """Revert the migration."""
    op.drop_index(op.f('ix_ai_documents_id'), table_name='ai_documents')
    op.drop_table('ai_documents')
    op.execute('DROP EXTENSION IF EXISTS vector')


# ==================== MANUAL SQL (if not using Alembic) ====================

"""
If you're not using Alembic, run this SQL directly in your PostgreSQL database:

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create ai_documents table
CREATE TABLE ai_documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    source TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX ix_ai_documents_id ON ai_documents(id);
CREATE INDEX ON ai_documents USING hnsw (embedding vector_cosine_ops);
"""
