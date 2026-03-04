"""
Document ingestion pipeline.
Orchestrates: file detection → parsing → metadata extraction → SQLite storage → index update.
"""
import os
import shutil
from logging_config.logger import ingestion_logger, error_logger
from database.connection import get_db, init_db
from ingestion.parsers import get_parser, SUPPORTED_EXTENSIONS, PageData
from config import UPLOAD_DIR


def ingest_document(file_path: str, original_filename: str = "") -> dict:
    """
    Ingest a document into the system.

    Returns:
        dict with keys: document_id, filename, total_pages, status
    """
    if not original_filename:
        original_filename = os.path.basename(file_path)

    ext = os.path.splitext(original_filename)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {ext}. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    ingestion_logger.info(f"Starting ingestion: {original_filename}")

    # Step 1: Ensure database is initialized
    init_db()

    # Step 2: Create document record (status='processing')
    file_type = ext.lstrip(".")
    with get_db() as db:
        cursor = db.execute(
            "INSERT INTO documents (filename, file_type, status) VALUES (?, ?, 'processing')",
            (original_filename, file_type),
        )
        document_id = cursor.lastrowid

    try:
        # Step 3: Parse document into pages
        parser_class = get_parser(file_path)
        if parser_class is None:
            raise ValueError(f"No parser found for {ext}")

        pages: list[PageData] = parser_class.parse(file_path)
        ingestion_logger.info(f"Parsed {len(pages)} pages from {original_filename}")

        if not pages:
            with get_db() as db:
                db.execute(
                    "UPDATE documents SET status='empty', total_pages=0 WHERE id=?",
                    (document_id,),
                )
            return {
                "document_id": document_id,
                "filename": original_filename,
                "total_pages": 0,
                "status": "empty",
            }

        # Step 4: Extract document title from first page
        doc_title = pages[0].title or original_filename

        # Step 5: Store pages in SQLite
        with get_db() as db:
            for page in pages:
                db.execute(
                    """INSERT INTO pages
                    (document_id, page_number, title, section_heading, keywords, content, token_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        document_id,
                        page.page_number,
                        page.title or doc_title,
                        page.section_heading,
                        page.keywords,
                        page.content,
                        page.token_count,
                    ),
                )

            # Update document record
            db.execute(
                "UPDATE documents SET title=?, total_pages=?, status='indexed' WHERE id=?",
                (doc_title, len(pages), document_id),
            )

        # Step 6: Trigger search index update
        _update_search_index(document_id)

        ingestion_logger.info(
            f"Ingestion complete: {original_filename} → "
            f"doc_id={document_id}, pages={len(pages)}"
        )

        return {
            "document_id": document_id,
            "filename": original_filename,
            "total_pages": len(pages),
            "status": "indexed",
        }

    except Exception as e:
        error_logger.error(f"Ingestion failed for {original_filename}: {e}")
        with get_db() as db:
            db.execute(
                "UPDATE documents SET status='error' WHERE id=?",
                (document_id,),
            )
        raise


def _update_search_index(document_id: int):
    """Trigger Whoosh index update for the given document's pages."""
    try:
        from rag_engine.indexing import add_document_to_index
        add_document_to_index(document_id)
    except ImportError:
        ingestion_logger.warning(
            "rag_engine.indexing not available yet — skipping index update"
        )
    except Exception as e:
        error_logger.error(f"Index update failed for doc_id={document_id}: {e}")


def delete_document(document_id: int):
    """Delete a document and all its pages from DB and search index."""
    with get_db() as db:
        db.execute("DELETE FROM pages WHERE document_id=?", (document_id,))
        db.execute("DELETE FROM documents WHERE id=?", (document_id,))

    try:
        from rag_engine.indexing import delete_document_from_index
        delete_document_from_index(document_id)
    except ImportError:
        pass

    ingestion_logger.info(f"Deleted document id={document_id}")


def list_documents() -> list[dict]:
    """List all documents with their metadata."""
    from database.connection import fetch_all
    return fetch_all(
        "SELECT id, filename, file_type, title, upload_date, total_pages, status "
        "FROM documents ORDER BY upload_date DESC"
    )


def get_document(document_id: int) -> dict | None:
    """Get a single document's metadata."""
    from database.connection import fetch_one
    return fetch_one("SELECT * FROM documents WHERE id=?", (document_id,))


def get_document_pages(document_id: int) -> list[dict]:
    """Get all pages for a document."""
    from database.connection import fetch_all
    return fetch_all(
        "SELECT * FROM pages WHERE document_id=? ORDER BY page_number",
        (document_id,),
    )
