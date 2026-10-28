CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE notice ADD COLUMN IF NOT EXISTS embedding vector(384);

-- Run this line only AFTER embed_notices.py has finished:
-- CREATE INDEX IF NOT EXISTS notice_embedding_idx ON notice USING hnsw (embedding vector_cosine_ops);
