"""
SQLite database schema for the RAG Document Assistant.
Tables: documents, pages, conversations, messages.
Performance indexes on foreign keys. WAL mode enabled.
"""

SCHEMA_SQL = """
-- ── Documents ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    title TEXT,
    upload_date TEXT DEFAULT (datetime('now')),
    total_pages INTEGER DEFAULT 0,
    status TEXT DEFAULT 'processing'
);

-- ── Pages (fundamental retrieval unit) ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS pages (
    page_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    title TEXT,
    section_heading TEXT,
    keywords TEXT,
    content TEXT NOT NULL,
    token_count INTEGER DEFAULT 0
);

-- ── Conversations ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT DEFAULT (datetime('now')),
    title TEXT,
    summary TEXT
);

-- ── Messages ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    sources_json TEXT,
    timestamp TEXT DEFAULT (datetime('now'))
);

-- ── Performance Indexes ──────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_pages_document_id ON pages(document_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
"""
