-- ====================================================================
-- Nelson Pediatrics Dataset - Production SQL Schema
-- Optimized for RAG systems and medical knowledge bases
-- Compatible with PostgreSQL, MySQL 8.0+, and SQLite 3.35+
-- ====================================================================

-- Main table for pediatric content chunks
CREATE TABLE IF NOT EXISTS pediatrics_chunks (
    id SERIAL PRIMARY KEY,
    
    -- Book metadata
    book_title VARCHAR(200) NOT NULL DEFAULT 'Nelson Textbook of Pediatrics',
    book_edition VARCHAR(50) DEFAULT '22nd Edition',
    
    -- Chapter information
    chapter_number INT NOT NULL,
    chapter_name VARCHAR(300) NOT NULL,
    
    -- Content organization
    topic_name VARCHAR(500),
    category VARCHAR(200),
    
    -- Main content fields
    content TEXT NOT NULL,              -- Full chunk text for embedding and RAG
    summary TEXT,                       -- Clinical summary (3-5 sentences)
    
    -- Metadata
    content_length INT GENERATED ALWAYS AS (LENGTH(content)) STORED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_chapter_positive CHECK (chapter_number > 0),
    CONSTRAINT chk_content_not_empty CHECK (LENGTH(TRIM(content)) > 0)
);

-- ====================================================================
-- INDEXES FOR PERFORMANCE
-- ====================================================================

-- Fast lookup by chapter
CREATE INDEX idx_pediatrics_chapter_num
ON pediatrics_chunks (chapter_number);

-- Fast lookup by category
CREATE INDEX idx_pediatrics_category
ON pediatrics_chunks (category);

-- Compound index for category + chapter queries
CREATE INDEX idx_pediatrics_cat_chapter
ON pediatrics_chunks (category, chapter_number);

-- Full-text search on content (PostgreSQL)
CREATE INDEX idx_pediatrics_content_fts
ON pediatrics_chunks
USING GIN (to_tsvector('english', content));

-- Full-text search on summary (PostgreSQL)
CREATE INDEX idx_pediatrics_summary_fts
ON pediatrics_chunks
USING GIN (to_tsvector('english', summary));

-- ====================================================================
-- MYSQL FULL-TEXT INDEXES (Comment out if using PostgreSQL)
-- ====================================================================

-- ALTER TABLE pediatrics_chunks ADD FULLTEXT INDEX idx_content_fulltext (content);
-- ALTER TABLE pediatrics_chunks ADD FULLTEXT INDEX idx_summary_fulltext (summary);

-- ====================================================================
-- VIEWS FOR COMMON QUERIES
-- ====================================================================

-- View: Chapters with chunk counts
CREATE OR REPLACE VIEW v_chapter_summary AS
SELECT 
    chapter_number,
    chapter_name,
    category,
    COUNT(*) as chunk_count,
    AVG(content_length) as avg_chunk_length,
    MIN(created_at) as first_added
FROM pediatrics_chunks
GROUP BY chapter_number, chapter_name, category
ORDER BY chapter_number;

-- View: Category statistics
CREATE OR REPLACE VIEW v_category_stats AS
SELECT 
    category,
    COUNT(*) as total_chunks,
    COUNT(DISTINCT chapter_number) as chapter_count,
    AVG(content_length) as avg_content_length
FROM pediatrics_chunks
GROUP BY category
ORDER BY total_chunks DESC;

-- ====================================================================
-- SAMPLE QUERIES FOR RAG APPLICATIONS
-- ====================================================================

/*
-- Search by keyword (PostgreSQL full-text)
SELECT id, chapter_name, topic_name, summary
FROM pediatrics_chunks
WHERE to_tsvector('english', content) @@ to_tsquery('english', 'pneumonia & treatment');

-- Search by category and chapter
SELECT *
FROM pediatrics_chunks
WHERE category = 'Respiratory Diseases'
  AND chapter_number BETWEEN 600 AND 650;

-- Get all chunks from a specific chapter
SELECT topic_name, summary, content
FROM pediatrics_chunks
WHERE chapter_number = 125
ORDER BY id;

-- Find chapters by content length
SELECT chapter_name, chunk_count, avg_chunk_length
FROM v_chapter_summary
WHERE avg_chunk_length > 2000
ORDER BY avg_chunk_length DESC;
*/

-- ====================================================================
-- DATA QUALITY CHECKS
-- ====================================================================

-- Check for missing summaries
-- SELECT COUNT(*) as missing_summaries
-- FROM pediatrics_chunks
-- WHERE summary IS NULL OR TRIM(summary) = '';

-- Check for very short content (possible issues)
-- SELECT id, chapter_name, content_length
-- FROM pediatrics_chunks
-- WHERE content_length < 100
-- ORDER BY content_length;

-- ====================================================================
-- COMMENTS
-- ====================================================================

COMMENT ON TABLE pediatrics_chunks IS 'Nelson Textbook of Pediatrics - Chunked content for RAG systems';
COMMENT ON COLUMN pediatrics_chunks.content IS 'Full text chunk for embedding generation and retrieval';
COMMENT ON COLUMN pediatrics_chunks.summary IS 'Clinical summary (3-5 sentences) for quick reference';
COMMENT ON COLUMN pediatrics_chunks.category IS 'Medical specialty category for organization';
