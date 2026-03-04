"""
Pydantic request/response models for the API.
"""
from pydantic import BaseModel, Field
from typing import Optional


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")
    conversation_id: Optional[int] = Field(None, description="Resume existing conversation")


class SourceInfo(BaseModel):
    page_id: int
    document_id: int
    page_number: int
    title: str = ""
    snippet: str = ""
    score: float = 0.0


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceInfo] = []
    conversation_id: int


# ── Documents ─────────────────────────────────────────────────────────────────

class DocumentInfo(BaseModel):
    id: int
    filename: str
    file_type: str
    title: Optional[str] = None
    upload_date: Optional[str] = None
    total_pages: int = 0
    status: str = "processing"


class DocumentUploadResponse(BaseModel):
    document_id: int
    filename: str
    total_pages: int
    status: str


class PageInfo(BaseModel):
    page_id: int
    document_id: int
    page_number: int
    title: Optional[str] = None
    section_heading: Optional[str] = None
    keywords: Optional[str] = None
    content: str = ""
    token_count: int = 0


# ── Search ────────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=50)


class SearchResult(BaseModel):
    page_id: int
    document_id: int
    page_number: int
    title: str = ""
    snippet: str = ""
    score: float = 0.0


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str


# ── Conversations ─────────────────────────────────────────────────────────────

class ConversationInfo(BaseModel):
    id: int
    created_at: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None


class MessageInfo(BaseModel):
    id: int
    role: str
    content: str
    sources_json: Optional[str] = None
    timestamp: Optional[str] = None


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    model: str
    documents_count: int
    index_ready: bool
