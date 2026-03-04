"""
Structured logging for the RAG Document Assistant.
Tracks: search queries, retrieval results, LLM latency, errors, index updates.
"""
import logging
import os
from config import LOG_DIR


def get_logger(name: str) -> logging.Logger:
    """Create a named logger that writes to data/logs/<name>.log."""
    logger = logging.getLogger(f"rag_assistant.{name}")

    # Avoid duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # File handler
    fh = logging.FileHandler(os.path.join(LOG_DIR, f"{name}.log"), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(fh)

    # Console handler (INFO+ only)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)s | %(message)s"))
    logger.addHandler(ch)

    return logger


# ── Pre-configured loggers ────────────────────────────────────────────────────
search_logger = get_logger("search")     # queries, retrieval results
llm_logger = get_logger("llm")           # prompts, latency, responses
index_logger = get_logger("index")       # index builds, updates
error_logger = get_logger("error")       # errors & exceptions
ingestion_logger = get_logger("ingestion")  # document parsing events
