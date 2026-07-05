-- Purpose: Database schema bootstrap for Supabase PostgreSQL.
-- Defines pgvector, the documents table, indexes, and an updated_at trigger.
-- Interactions: Applied manually in Supabase SQL Editor or via
-- apps/backend/scripts/apply_init_db.py. Required before document_repository.py
-- can insert or query document metadata.
--
-- Run this once in Supabase: Dashboard -> SQL Editor -> New query -> Run

CREATE EXTENSION IF NOT EXISTS vector;

-- Phase 2: documents table for PDF upload and library metadata
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'upload',
    acquisition_mode TEXT NOT NULL DEFAULT 'user_upload',
    status TEXT NOT NULL DEFAULT 'uploaded',
    file_path TEXT NOT NULL,
    page_count INTEGER,
    source_url TEXT,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    retrieved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents (status);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS documents_updated_at ON documents;
CREATE TRIGGER documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Phase 3: document_chunks table for extracted PDF text chunks
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    page_number INTEGER,
    section_title TEXT,
    token_count INTEGER NOT NULL,
    embedding vector,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id_chunk_index
    ON document_chunks (document_id, chunk_index);
