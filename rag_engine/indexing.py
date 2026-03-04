"""
Whoosh-based inverted index with BM25 scoring.
Manages: index creation, page addition, deletion, and search.
"""
import os
from whoosh import index
from whoosh.fields import Schema, ID, TEXT, KEYWORD, NUMERIC, STORED
from whoosh.analysis import StemmingAnalyzer
from whoosh.qparser import MultifieldParser, OrGroup
from whoosh.scoring import BM25F
from whoosh import writing

from config import INDEX_DIR
from logging_config.logger import index_logger


# ── Index Schema ──────────────────────────────────────────────────────────────

SCHEMA = Schema(
    page_id=ID(stored=True, unique=True),
    document_id=ID(stored=True),
    title=TEXT(stored=True, analyzer=StemmingAnalyzer()),
    section_heading=TEXT(stored=True, analyzer=StemmingAnalyzer()),
    keywords=KEYWORD(stored=True, commas=True, scorable=True),
    content=TEXT(stored=True, analyzer=StemmingAnalyzer()),
    page_number=NUMERIC(stored=True, signed=False),
)


def get_or_create_index():
    """Open existing index or create a new one."""
    if index.exists_in(INDEX_DIR):
        return index.open_dir(INDEX_DIR)
    else:
        os.makedirs(INDEX_DIR, exist_ok=True)
        ix = index.create_in(INDEX_DIR, SCHEMA)
        index_logger.info(f"Created new search index at {INDEX_DIR}")
        return ix


def add_pages_to_index(pages: list[dict]):
    """
    Add a list of pages to the Whoosh index.
    Each page dict must have: page_id, document_id, title, section_heading,
    keywords, content, page_number.
    """
    ix = get_or_create_index()
    writer = ix.writer()

    for page in pages:
        writer.update_document(
            page_id=str(page["page_id"]),
            document_id=str(page["document_id"]),
            title=page.get("title", ""),
            section_heading=page.get("section_heading", ""),
            keywords=page.get("keywords", ""),
            content=page.get("content", ""),
            page_number=page.get("page_number", 0),
        )

    writer.commit()
    index_logger.info(f"Indexed {len(pages)} pages")


def add_document_to_index(document_id: int):
    """Index all pages for a given document from the database."""
    from database.connection import fetch_all

    pages = fetch_all(
        "SELECT page_id, document_id, title, section_heading, keywords, content, page_number "
        "FROM pages WHERE document_id=?",
        (document_id,),
    )

    if pages:
        add_pages_to_index(pages)
        index_logger.info(f"Indexed document {document_id}: {len(pages)} pages")


def delete_document_from_index(document_id: int):
    """Remove all pages for a document from the index."""
    ix = get_or_create_index()
    writer = ix.writer()

    # Find and delete all pages with this document_id
    with ix.searcher() as searcher:
        from whoosh.query import Term
        results = searcher.search(Term("document_id", str(document_id)), limit=None)
        for hit in results:
            writer.delete_by_term("page_id", hit["page_id"])

    writer.commit()
    index_logger.info(f"Removed document {document_id} from index")


def search(query_str: str, top_k: int = 15) -> list[dict]:
    """
    Search the index using BM25 scoring.

    Returns a list of dicts with:
        page_id, document_id, title, section_heading, content, page_number, score
    """
    ix = get_or_create_index()

    with ix.searcher(weighting=BM25F()) as searcher:
        # Search across content, title, section_heading, and keywords
        parser = MultifieldParser(
            ["content", "title", "section_heading", "keywords"],
            schema=ix.schema,
            group=OrGroup,
        )
        query = parser.parse(query_str)
        results = searcher.search(query, limit=top_k)

        hits = []
        for hit in results:
            hits.append({
                "page_id": int(hit["page_id"]),
                "document_id": int(hit["document_id"]),
                "title": hit.get("title", ""),
                "section_heading": hit.get("section_heading", ""),
                "content": hit.get("content", ""),
                "page_number": hit.get("page_number", 0),
                "score": hit.score,
            })

        return hits


def rebuild_index():
    """Rebuild the entire index from the database."""
    from database.connection import fetch_all

    # Clear existing index
    if os.path.exists(INDEX_DIR):
        import shutil
        shutil.rmtree(INDEX_DIR)

    os.makedirs(INDEX_DIR, exist_ok=True)
    ix = index.create_in(INDEX_DIR, SCHEMA)

    pages = fetch_all(
        "SELECT page_id, document_id, title, section_heading, keywords, content, page_number "
        "FROM pages"
    )

    if pages:
        add_pages_to_index(pages)

    index_logger.info(f"Rebuilt index: {len(pages)} total pages")
