"""
Agent tools: search, get, summarize, and cite operations.
All LLM calls go through llm_client — never call Ollama directly.
"""
from rag_engine.retrieval import search_pages, get_page
from rag_engine.context_builder import build_context
from rag_engine.snippet_extractor import Snippet
from logging_config.logger import search_logger


def tool_search_pages(query: str) -> tuple[str, list[dict]]:
    """
    Search for relevant snippets and build context.

    Returns:
        Tuple of (context_xml, sources_list)
    """
    snippets = search_pages(query)
    if not snippets:
        return "", []
    return build_context(snippets)


def tool_get_page(page_id: int) -> dict | None:
    """Fetch a page's full content by page_id."""
    return get_page(page_id)


def tool_summarize_pages(page_ids: list[int]) -> str:
    """
    Generate a summary across multiple pages using the LLM.
    """
    from llm_client import get_llm_client
    from database.connection import fetch_all

    pages = fetch_all(
        "SELECT page_id, title, section_heading, content FROM pages WHERE page_id IN ({})".format(
            ",".join("?" for _ in page_ids)
        ),
        tuple(page_ids),
    )

    if not pages:
        return "No pages found for the given IDs."

    page_texts = []
    for p in pages:
        page_texts.append(f"[Page {p['page_id']}] {p.get('title', '')}\n{p['content']}")

    combined = "\n\n---\n\n".join(page_texts)
    prompt = f"""Summarize the following document pages concisely. Focus on the key information.

{combined}

Summary:"""

    client = get_llm_client()
    return client.generate(prompt)


def tool_cite_sources(sources: list[dict]) -> str:
    """
    Generate formatted citations from source metadata.

    Args:
        sources: List of dicts with page_id, document_id, page_number, title, snippet
    """
    if not sources:
        return "No sources to cite."

    citations = []
    for i, src in enumerate(sources, 1):
        title = src.get("title", "Unknown")
        page_num = src.get("page_number", "?")
        snippet = src.get("snippet", "")
        preview = snippet[:150] + "..." if len(snippet) > 150 else snippet
        citations.append(f"[{i}] {title} — Page {page_num}\n    \"{preview}\"")

    return "\n\n".join(citations)
