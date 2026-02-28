-- Enable pgvector extension for vector operations
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable uuid-ossp extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create documents_vectors table for storing vector embeddings
CREATE TABLE IF NOT EXISTS documents_vectors (
    id UUID DEFAULT uuid_generate_v4() NOT NULL PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL, -- The text content that was embedded
    embedding vector(1536), -- Vector embedding (1536 dimensions for OpenAI text-embedding-3-small/ada-002)
    metadata JSONB DEFAULT '{}'::jsonb, -- Additional metadata for the chunk
    chunk_index INTEGER DEFAULT 0, -- Index of the chunk within the document
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
);

-- Create indexes for efficient vector similarity search
CREATE INDEX IF NOT EXISTS idx_documents_vectors_document_id ON documents_vectors(document_id);
CREATE INDEX IF NOT EXISTS idx_documents_vectors_embedding ON documents_vectors USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Add a function to search for similar vectors
CREATE OR REPLACE FUNCTION search_similar_vectors(
    query_embedding vector(1536),
    similarity_threshold float DEFAULT 0.5,
    max_results integer DEFAULT 10
)
RETURNS TABLE(
    id UUID,
    document_id UUID,
    content TEXT,
    similarity FLOAT,
    metadata JSONB,
    chunk_index INTEGER,
    document_name TEXT,
    document_source TEXT,
    document_metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dv.id,
        dv.document_id,
        dv.content,
        1 - (dv.embedding <=> query_embedding) as similarity,
        dv.metadata,
        dv.chunk_index,
        d.original_filename::text as document_name,
        d.storage_path::text as document_source,
        d.metadata as document_metadata
    FROM documents_vectors dv
    JOIN documents d ON dv.document_id = d.id
    WHERE 1 - (dv.embedding <=> query_embedding) > similarity_threshold
    ORDER BY dv.embedding <=> query_embedding
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Add a function for hybrid search combining vector similarity and text search
CREATE OR REPLACE FUNCTION search_hybrid_vectors(
    query_embedding vector(1536),
    query_text TEXT,
    similarity_threshold float DEFAULT 0.5,
    max_results integer DEFAULT 10,
    vector_weight float DEFAULT 0.6
)
RETURNS TABLE(
    id UUID,
    document_id UUID,
    content TEXT,
    similarity DOUBLE PRECISION,
    text_rank DOUBLE PRECISION,
    combined_score DOUBLE PRECISION,
    metadata JSONB,
    chunk_index INTEGER,
    document_name TEXT,
    document_source TEXT,
    document_metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dv.id,
        dv.document_id,
        dv.content,
        (1 - (dv.embedding <=> query_embedding))::double precision as similarity,
        ts_rank_cd(to_tsvector('indonesian', dv.content), plainto_tsquery('indonesian', query_text))::double precision as text_rank,
        (
            vector_weight * (1 - (dv.embedding <=> query_embedding))::double precision
        ) + (
            (1 - vector_weight) * ts_rank_cd(to_tsvector('indonesian', dv.content), plainto_tsquery('indonesian', query_text))::double precision
        ) as combined_score,
        dv.metadata,
        dv.chunk_index,
        d.original_filename::text as document_name,
        d.storage_path::text as document_source,
        d.metadata as document_metadata
    FROM documents_vectors dv
    JOIN documents d ON dv.document_id = d.id
    WHERE 1 - (dv.embedding <=> query_embedding) > similarity_threshold
    ORDER BY combined_score DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Add text search index for hybrid search
CREATE INDEX IF NOT EXISTS idx_documents_vectors_content_tsvector 
ON documents_vectors USING gin(to_tsvector('indonesian', content));
