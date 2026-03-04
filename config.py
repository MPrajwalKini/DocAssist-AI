"""
Central configuration for the RAG Document Assistant.
All settings are configurable via environment variables or .env file.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM Provider ─────────────────────────────────────────────────────────────
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "ollama")  # "ollama" | "openai" | "anthropic"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3")
FALLBACK_MODELS = ["phi3", "mistral"]
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "120"))

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(DATA_DIR, "llm_assistant.db"))
INDEX_DIR = os.getenv("INDEX_DIR", os.path.join(DATA_DIR, "search_index"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(DATA_DIR, "uploads"))
LOG_DIR = os.getenv("LOG_DIR", os.path.join(DATA_DIR, "logs"))

# ── Retrieval ─────────────────────────────────────────────────────────────────
BM25_TOP_K = 15                # Stage 1: BM25 candidate pages
SNIPPETS_PER_PAGE = 3          # Stage 2: top snippets per page
RERANK_TOP_K = 5               # Stage 3: LLM re-ranked final snippets
CONTEXT_TOKEN_BUDGET = 8000    # Max tokens for context window
RETRIEVAL_MIN_QUERY_LEN = 5    # Skip retrieval for queries shorter than this

# ── Memory ────────────────────────────────────────────────────────────────────
MAX_CONVERSATION_MESSAGES = 20

# ── Ensure data directories exist ─────────────────────────────────────────────
for d in [DATA_DIR, INDEX_DIR, UPLOAD_DIR, LOG_DIR]:
    os.makedirs(d, exist_ok=True)
