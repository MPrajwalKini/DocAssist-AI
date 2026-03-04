# ◆ DocAssist AI — RAG Document Assistant

A production-grade document assistant that ingests large document collections, indexes them by page, and answers questions with **grounded citations** — powered by classical information retrieval (BM25) and a local LLM via **Ollama**.

> **No vector databases.** Retrieval uses Whoosh inverted indexes with BM25 scoring, query expansion, and passage-level snippet extraction.

---

## Features

- **Multi-format ingestion** — PDF, DOCX, TXT, Markdown, HTML
- **Page-level indexing** — Whoosh BM25 with stemming analyzer
- **Three-stage retrieval** — BM25 → snippet extraction → LLM re-ranking
- **Grounded answers** — citations with document name, page number, and quoted text
- **Conversation memory** — persistent chat history in SQLite
- **Modular LLM client** — Ollama (default), OpenAI-compatible APIs
- **Structured logging** — search queries, LLM latency, index updates, errors
- **Claude-style UI** — dark theme, expandable citations, drag-drop upload

---

## Architecture

```
User uploads document
    → Parser extracts pages (PDF/DOCX/TXT/MD/HTML)
    → Pages stored in SQLite
    → Pages indexed in Whoosh (BM25)

User asks question
    → Query expansion (synonyms + stemming)
    → BM25 search → top 15 pages
    → Snippet extraction → scored sentences
    → LLM re-ranks → top 5 snippets
    → Context builder → XML with page_ids
    → Ollama generates grounded answer with citations
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI |
| Indexing | Whoosh (BM25 / TF-IDF) |
| Database | SQLite (WAL mode) |
| LLM | Ollama (llama3) |
| Frontend | React, Vite |

---

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **Ollama** — [install from ollama.com](https://ollama.com)

### 1. Pull the LLM model

```bash
ollama pull llama3
```

### 2. Install Python dependencies

```bash
cd "DocAssist-AI"  # Navigate to the project directory
pip install -r requirements.txt
```

### 3. Start the backend

```bash
python -m uvicorn main:app --reload --port 8000
```

### 4. Install and start the frontend

```bash
cd ui
npm install
npm run dev
```

### 5. Open the app

Navigate to **http://localhost:5173** in your browser.

---

## Usage

1. **Upload a document** — drag and drop or click the upload zone (supports PDF, DOCX, TXT, MD, HTML)
2. **Wait for indexing** — the progress indicator shows when indexing is complete
3. **Ask a question** — type a question about your documents
4. **View citations** — click the source chips to expand and see the quoted passage

---

## Project Structure

```
LLM/
├── main.py                     # FastAPI entry point
├── config.py                   # Central configuration
├── llm_client.py               # Modular LLM provider client
├── requirements.txt
├── .env.example
├── progress.md                 # Root progress tracker
│
├── database/
│   ├── connection.py           # SQLite + WAL mode
│   ├── models.py               # Schema + indexes
│   └── progress.md
│
├── ingestion/
│   ├── parsers.py              # PDF, DOCX, TXT, MD, HTML
│   ├── pipeline.py             # Orchestration pipeline
│   └── progress.md
│
├── rag_engine/
│   ├── indexing.py             # Whoosh BM25 index
│   ├── query_expansion.py      # Synonyms + stemming
│   ├── snippet_extractor.py    # Sentence-level passage scoring
│   ├── retrieval.py            # Three-stage retrieval pipeline
│   ├── context_builder.py      # XML context assembly
│   └── progress.md
│
├── agent/
│   ├── tools.py                # search, get, summarize, cite
│   ├── reasoning.py            # Grounded reasoning pipeline
│   ├── memory.py               # Conversation memory
│   └── progress.md
│
├── logging_config/
│   ├── logger.py               # Structured logging
│   └── progress.md
│
├── api/
│   ├── routes.py               # REST endpoints
│   ├── schemas.py              # Pydantic models
│   └── progress.md
│
└── ui/                         # React (Vite) frontend
    ├── src/
    │   ├── App.jsx
    │   ├── index.css
    │   └── components/
    │       ├── ChatInterface.jsx
    │       ├── SourceCitation.jsx
    │       ├── DocumentUpload.jsx
    │       └── Sidebar.jsx
    └── progress.md
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | System status + Ollama check |
| `POST` | `/api/documents/upload` | Upload and ingest a document |
| `GET` | `/api/documents` | List all documents |
| `GET` | `/api/documents/{id}` | Get document details |
| `DELETE` | `/api/documents/{id}` | Delete a document |
| `GET` | `/api/documents/{id}/pages` | List pages for a document |
| `POST` | `/api/chat` | Send message, get grounded response |
| `POST` | `/api/search` | Direct page search |
| `GET` | `/api/conversations` | List conversations |
| `GET` | `/api/conversations/{id}` | Get conversation messages |

Interactive API docs available at **http://localhost:8000/docs** (Swagger UI).

---

## Configuration

All settings are in `config.py` and can be overridden via environment variables (`.env` file):

| Setting | Default | Description |
|---------|---------|-------------|
| `MODEL_PROVIDER` | `ollama` | LLM provider (`ollama`, `openai`) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `MODEL_NAME` | `llama3` | Model to use |
| `BM25_TOP_K` | `15` | Pages from BM25 search |
| `SNIPPETS_PER_PAGE` | `3` | Snippets extracted per page |
| `RERANK_TOP_K` | `5` | Final snippets after LLM re-rank |
| `CONTEXT_TOKEN_BUDGET` | `8000` | Max tokens for context window |
| `REQUEST_TIMEOUT` | `120` | LLM request timeout (seconds) |

---

## Progress Tracking

Every module directory contains a `progress.md` file that tracks component development state. Before modifying any module, read its `progress.md` to understand current status and update it after making changes.

---

## License

MIT
