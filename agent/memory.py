"""
Conversation memory management.
Short-term: last N messages from SQLite.
Token-limited trimming. Optional LLM-generated summary.
"""
from database.connection import get_db, fetch_all, fetch_one, execute
from config import MAX_CONVERSATION_MESSAGES
from ingestion.parsers import estimate_tokens


def create_conversation(title: str = "New Conversation") -> int:
    """Create a new conversation and return its ID."""
    return execute(
        "INSERT INTO conversations (title) VALUES (?)",
        (title[:200],),
    )


def save_message(
    conversation_id: int,
    role: str,
    content: str,
    sources_json: str | None = None,
):
    """Save a message to a conversation."""
    execute(
        "INSERT INTO messages (conversation_id, role, content, sources_json) VALUES (?, ?, ?, ?)",
        (conversation_id, role, content, sources_json),
    )


def get_conversation_history(
    conversation_id: int,
    max_messages: int = MAX_CONVERSATION_MESSAGES,
) -> list[dict]:
    """
    Get recent messages for a conversation.
    Trims to max_messages, keeping the most recent.
    """
    messages = fetch_all(
        "SELECT role, content, sources_json, timestamp FROM messages "
        "WHERE conversation_id=? ORDER BY timestamp ASC",
        (conversation_id,),
    )

    # Keep only the most recent messages
    if len(messages) > max_messages:
        messages = messages[-max_messages:]

    return messages


def list_conversations() -> list[dict]:
    """List all conversations, most recent first."""
    return fetch_all(
        "SELECT id, created_at, title, summary FROM conversations ORDER BY created_at DESC"
    )


def get_conversation(conversation_id: int) -> dict | None:
    """Get a single conversation's metadata."""
    return fetch_one("SELECT * FROM conversations WHERE id=?", (conversation_id,))


def get_conversation_messages(conversation_id: int) -> list[dict]:
    """Get all messages for a conversation."""
    return fetch_all(
        "SELECT id, role, content, sources_json, timestamp FROM messages "
        "WHERE conversation_id=? ORDER BY timestamp ASC",
        (conversation_id,),
    )


def update_conversation_title(conversation_id: int, title: str):
    """Update a conversation's title."""
    with get_db() as db:
        db.execute("UPDATE conversations SET title=? WHERE id=?", (title[:200], conversation_id))


def delete_conversation(conversation_id: int):
    """Delete a conversation and all its messages."""
    with get_db() as db:
        db.execute("DELETE FROM messages WHERE conversation_id=?", (conversation_id,))
        db.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))
