"""
Agent reasoning pipeline.
Orchestrates: retrieval decision → context building → LLM answer generation with citations.

Retrieval trigger is deterministic: if query length > 5 chars, run retrieval.
"""
import json
from llm_client import get_llm_client
from agent.tools import tool_search_pages, tool_cite_sources
from agent.memory import get_conversation_history, save_message, create_conversation
from logging_config.logger import llm_logger, search_logger
from config import RETRIEVAL_MIN_QUERY_LEN


# ── System Prompt Template ────────────────────────────────────────────────────

SYSTEM_PROMPT_WITH_CONTEXT = """You are an intelligent document assistant. You answer questions using ONLY the provided context documents.

INSTRUCTIONS:
1. Read the context documents carefully.
2. Find relevant passages that answer the user's question.
3. Quote the relevant text before giving your answer.
4. Always cite your sources using the format: [Source: Title — Page N]
5. If the context does not contain enough information to answer, say so clearly.
6. Do NOT make up information that is not in the provided context.

{context}

CONVERSATION HISTORY:
{history}
"""

SYSTEM_PROMPT_NO_CONTEXT = """You are an intelligent document assistant. You can help users with questions about their uploaded documents.

Currently, no relevant documents were found for this query. You may:
1. Answer general questions to the best of your ability
2. Suggest the user upload relevant documents
3. Help rephrase their question for better search results

CONVERSATION HISTORY:
{history}
"""

SYSTEM_PROMPT_GREETING = """You are a friendly document assistant. Respond naturally to greetings and casual conversation. Keep responses brief.

CONVERSATION HISTORY:
{history}
"""


# ── Response Model ────────────────────────────────────────────────────────────

class AgentResponse:
    """Structured response from the agent."""

    def __init__(self, answer: str, sources: list[dict] = None, conversation_id: int = None):
        self.answer = answer
        self.sources = sources or []
        self.conversation_id = conversation_id

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "sources": self.sources,
            "conversation_id": self.conversation_id,
        }


# ── Main Reasoning Pipeline ──────────────────────────────────────────────────

def process_query(
    query: str,
    conversation_id: int | None = None,
) -> AgentResponse:
    """
    Main entry point: process a user query and generate a grounded response.

    Pipeline:
        1. Create or resume conversation
        2. Decide if retrieval is needed (deterministic: query length > 5)
        3. If yes: search → build context → generate answer with citations
        4. If no: generate simple response
        5. Save messages to conversation history
    """
    client = get_llm_client()

    # Step 1: Conversation management
    if conversation_id is None:
        conversation_id = create_conversation(title=query[:100])

    # Save user message
    save_message(conversation_id, "user", query)

    # Get conversation history
    history = get_conversation_history(conversation_id)
    history_str = _format_history(history)

    # Step 2: Determine if retrieval is needed
    needs_retrieval = len(query.strip()) > RETRIEVAL_MIN_QUERY_LEN

    if not needs_retrieval:
        # Simple greeting / short query
        prompt = SYSTEM_PROMPT_GREETING.format(history=history_str)
        answer = client.generate(query, system_prompt=prompt)

        save_message(conversation_id, "assistant", answer)
        return AgentResponse(answer=answer, conversation_id=conversation_id)

    # Step 3: Retrieval + context building
    search_logger.info(f"Retrieval triggered for: {query}")
    context_xml, sources = tool_search_pages(query)

    if context_xml:
        # We have relevant context
        system_prompt = SYSTEM_PROMPT_WITH_CONTEXT.format(
            context=context_xml,
            history=history_str,
        )
    else:
        # No results found
        system_prompt = SYSTEM_PROMPT_NO_CONTEXT.format(history=history_str)

    # Step 4: Generate answer
    answer = client.generate(query, system_prompt=system_prompt)

    # Step 5: Save assistant response with sources
    sources_json = json.dumps(sources) if sources else None
    save_message(conversation_id, "assistant", answer, sources_json=sources_json)

    llm_logger.info(f"Response generated for conversation {conversation_id}")

    return AgentResponse(
        answer=answer,
        sources=sources,
        conversation_id=conversation_id,
    )


def _format_history(messages: list[dict], max_messages: int = 10) -> str:
    """Format recent conversation history for the prompt."""
    recent = messages[-max_messages:] if len(messages) > max_messages else messages

    if not recent:
        return "(No previous messages)"

    lines = []
    for msg in recent:
        role = msg["role"].upper()
        content = msg["content"]
        # Truncate long messages in history
        if len(content) > 500:
            content = content[:500] + "..."
        lines.append(f"{role}: {content}")

    return "\n".join(lines)
