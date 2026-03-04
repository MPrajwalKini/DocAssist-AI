"""
Context builder: assembles retrieved snippets into XML context for the LLM.
Handles deduplication and token budget enforcement.
"""
from rag_engine.snippet_extractor import Snippet
from ingestion.parsers import estimate_tokens
from config import CONTEXT_TOKEN_BUDGET


def build_context(snippets: list[Snippet], token_budget: int = CONTEXT_TOKEN_BUDGET) -> tuple[str, list[dict]]:
    """
    Build XML context from retrieved snippets.

    Args:
        snippets: Ranked list of Snippet objects from the retrieval pipeline
        token_budget: Maximum approximate token count for the context

    Returns:
        Tuple of (context_xml_string, sources_list)
        sources_list contains dicts with page_id, document_id, page_number, title, snippet
    """
    if not snippets:
        return "", []

    # Deduplicate: keep best snippet per (page_id, snippet_text) pair
    seen = set()
    deduped: list[Snippet] = []
    for s in snippets:
        key = (s.page_id, s.snippet[:100])  # Use first 100 chars as dedup key
        if key not in seen:
            seen.add(key)
            deduped.append(s)

    # Build context within token budget
    documents = []
    sources = []
    total_tokens = 0

    for i, snippet in enumerate(deduped):
        snippet_tokens = estimate_tokens(snippet.snippet)

        if total_tokens + snippet_tokens > token_budget:
            break

        total_tokens += snippet_tokens

        documents.append(
            f'  <document index="{i + 1}">\n'
            f'    <document_id>{snippet.document_id}</document_id>\n'
            f'    <page_id>{snippet.page_id}</page_id>\n'
            f'    <page_number>{snippet.page_number}</page_number>\n'
            f'    <title>{_escape_xml(snippet.title)}</title>\n'
            f'    <snippet>{_escape_xml(snippet.snippet)}</snippet>\n'
            f'  </document>'
        )

        sources.append({
            "page_id": snippet.page_id,
            "document_id": snippet.document_id,
            "page_number": snippet.page_number,
            "title": snippet.title,
            "snippet": snippet.snippet,
            "score": snippet.score,
        })

    if not documents:
        return "", []

    context_xml = "<context_documents>\n" + "\n".join(documents) + "\n</context_documents>"

    return context_xml, sources


def _escape_xml(text: str) -> str:
    """Escape special XML characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
