"""
FastAPI routes for the RAG Document Assistant.
Endpoints: chat, documents, search, conversations, health.
"""
import os
import shutil
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException
from api.schemas import (
    ChatRequest, ChatResponse, SourceInfo,
    DocumentInfo, DocumentUploadResponse, PageInfo,
    SearchRequest, SearchResponse, SearchResult,
    ConversationInfo, MessageInfo, HealthResponse,
)
from logging_config.logger import error_logger
from config import UPLOAD_DIR, MODEL_NAME
from database.connection import init_db

router = APIRouter(prefix="/api")


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check system status: Ollama connection, model, document count."""
    from llm_client import get_llm_client
    from database.connection import fetch_one
    from whoosh import index
    from config import INDEX_DIR

    client = get_llm_client()
    ollama_ok = client.check_health()

    doc_count = 0
    try:
        result = fetch_one("SELECT COUNT(*) as cnt FROM documents")
        doc_count = result["cnt"] if result else 0
    except Exception:
        pass

    index_ready = index.exists_in(INDEX_DIR) if os.path.exists(INDEX_DIR) else False

    return HealthResponse(
        status="ok" if ollama_ok else "degraded",
        ollama_connected=ollama_ok,
        model=MODEL_NAME,
        documents_count=doc_count,
        index_ready=index_ready,
    )


# ── Documents ─────────────────────────────────────────────────────────────────

@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload and ingest a document."""
    from ingestion.pipeline import ingest_document
    from ingestion.parsers import SUPPORTED_EXTENSIONS

    # Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    # Save upload to temp file
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    tmp_path = os.path.join(UPLOAD_DIR, file.filename or "upload.tmp")

    try:
        with open(tmp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        result = ingest_document(tmp_path, original_filename=file.filename or "unknown")

        return DocumentUploadResponse(**result)

    except Exception as e:
        error_logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", response_model=list[DocumentInfo])
async def list_documents():
    """List all ingested documents."""
    from ingestion.pipeline import list_documents as _list
    docs = _list()
    return [DocumentInfo(**d) for d in docs]


@router.get("/documents/{document_id}", response_model=DocumentInfo)
async def get_document(document_id: int):
    """Get a single document's details."""
    from ingestion.pipeline import get_document as _get
    doc = _get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentInfo(**doc)


@router.delete("/documents/{document_id}")
async def delete_document(document_id: int):
    """Delete a document and all its pages."""
    from ingestion.pipeline import get_document as _get, delete_document as _del
    doc = _get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    _del(document_id)
    return {"status": "deleted", "document_id": document_id}


@router.get("/documents/{document_id}/pages", response_model=list[PageInfo])
async def get_document_pages(document_id: int):
    """List all pages for a document."""
    from ingestion.pipeline import get_document_pages as _pages
    pages = _pages(document_id)
    return [PageInfo(**p) for p in pages]


# ── Chat ──────────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message and get a grounded response with citations."""
    from agent.reasoning import process_query

    try:
        result = process_query(
            query=request.message,
            conversation_id=request.conversation_id,
        )

        return ChatResponse(
            answer=result.answer,
            sources=[SourceInfo(**s) for s in result.sources],
            conversation_id=result.conversation_id,
        )

    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        error_logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Search ────────────────────────────────────────────────────────────────────

@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Direct page search without LLM reasoning."""
    from rag_engine.retrieval import search_pages

    snippets = search_pages(request.query)
    results = [
        SearchResult(
            page_id=s.page_id,
            document_id=s.document_id,
            page_number=s.page_number,
            title=s.title,
            snippet=s.snippet,
            score=s.score,
        )
        for s in snippets[:request.top_k]
    ]

    return SearchResponse(results=results, query=request.query)


# ── Conversations ─────────────────────────────────────────────────────────────

@router.get("/conversations", response_model=list[ConversationInfo])
async def list_conversations():
    """List all conversations."""
    from agent.memory import list_conversations as _list
    convos = _list()
    return [ConversationInfo(**c) for c in convos]


@router.get("/conversations/{conversation_id}", response_model=list[MessageInfo])
async def get_conversation(conversation_id: int):
    """Get all messages for a conversation."""
    from agent.memory import get_conversation_messages
    msgs = get_conversation_messages(conversation_id)
    if not msgs:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return [MessageInfo(**m) for m in msgs]


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int):
    """Delete a conversation and all its messages."""
    from agent.memory import delete_conversation as _del
    _del(conversation_id)
    return {"status": "deleted", "conversation_id": conversation_id}
