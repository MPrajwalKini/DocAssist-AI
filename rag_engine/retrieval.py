"""
Three-stage retrieval pipeline:
  Stage 1: BM25 search via Whoosh → top 15 pages
  Stage 2: Snippet extraction → scored sentence passages
  Stage 3: LLM re-ranking → top 5 final snippets
"""
import json
import re
from logging_config.logger import search_logger, error_logger
from rag_engine.indexing import search as whoosh_search
from rag_engine.query_expansion import expand_query
from rag_engine.snippet_extractor import extract_snippets, Snippet
from config import BM25_TOP_K, SNIPPETS_PER_PAGE, RERANK_TOP_K


def search_pages(query: str) -> list[Snippet]:
    """
    Full retrieval pipeline: query expansion → BM25 → snippet extraction → LLM rerank.

    Args:
        query: User's original search query

    Returns:
        List of top-ranked Snippet objects
    """
    search_logger.info(f"Query: {query}")

    # Stage 1: Query expansion + BM25 search
    expanded = expand_query(query)
    search_logger.info(f"Expanded query: {expanded}")

    pages = whoosh_search(expanded, top_k=BM25_TOP_K)
    search_logger.info(f"BM25 returned {len(pages)} pages")

    if not pages:
        return []

    # Stage 2: Snippet extraction
    snippets = extract_snippets(query, pages, top_n_per_page=SNIPPETS_PER_PAGE)
    search_logger.info(f"Extracted {len(snippets)} snippets")

    if not snippets:
        return []

    # Stage 3: LLM re-ranking
    try:
        reranked = llm_rerank(query, snippets, top_k=RERANK_TOP_K)
        search_logger.info(f"Re-ranked to {len(reranked)} snippets")
        return reranked
    except Exception as e:
        # If LLM re-ranking fails (e.g., Ollama down), fall back to BM25+snippet scores
        error_logger.warning(f"LLM re-ranking failed, using snippet scores: {e}")
        return snippets[:RERANK_TOP_K]


def llm_rerank(query: str, snippets: list[Snippet], top_k: int) -> list[Snippet]:
    """
    Use the LLM to re-rank candidate snippets by relevance to the query.

    The LLM receives a structured prompt asking it to score each snippet 0-10.
    """
    from llm_client import get_llm_client
    client = get_llm_client()

    # Build the re-ranking prompt
    snippet_texts = []
    for i, s in enumerate(snippets[:20]):  # Cap at 20 to respect context limits
        snippet_texts.append(f"[{i}] (page_id={s.page_id}) {s.snippet}")

    prompt = f"""You are a relevance scoring assistant. Given a user query and a list of text snippets, 
score each snippet's relevance to the query on a scale of 0-10.

Query: "{query}"

Snippets:
{chr(10).join(snippet_texts)}

Respond with ONLY a JSON array of scores in order, like: [8, 3, 9, 1, ...]
Do not include any other text."""

    try:
        response = client.generate(prompt)

        # Parse scores from LLM response
        scores = _parse_rerank_scores(response, len(snippets[:20]))

        # Apply LLM scores
        scored_snippets = []
        for i, s in enumerate(snippets[:20]):
            llm_score = scores[i] if i < len(scores) else 0
            # Combine: 70% LLM score + 30% original BM25/snippet score (normalized)
            max_original = max(sn.score for sn in snippets) if snippets else 1
            combined = 0.7 * llm_score + 0.3 * (s.score / max_original * 10)
            scored_snippets.append((s, combined))

        scored_snippets.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in scored_snippets[:top_k]]

    except Exception as e:
        error_logger.error(f"LLM rerank parsing error: {e}")
        return snippets[:top_k]


def _parse_rerank_scores(response: str, expected_count: int) -> list[float]:
    """Parse a JSON array of scores from the LLM response."""
    # Try to find a JSON array in the response
    match = re.search(r'\[[\d\s,.\-]+\]', response)
    if match:
        try:
            scores = json.loads(match.group())
            return [float(s) for s in scores]
        except (json.JSONDecodeError, ValueError):
            pass

    # Fallback: try to extract individual numbers
    numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', response)
    if numbers:
        return [float(n) for n in numbers[:expected_count]]

    # Last resort: equal scores
    return [5.0] * expected_count


def get_page(page_id: int) -> dict | None:
    """Fetch a single page's full content from the database."""
    from database.connection import fetch_one
    return fetch_one("SELECT * FROM pages WHERE page_id=?", (page_id,))
