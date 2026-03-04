"""
Passage-level snippet extractor.
Splits pages into sentences and scores them by keyword overlap with the query.
Returns the most relevant snippets — the fundamental unit for LLM re-ranking.
"""
import re
from dataclasses import dataclass


@dataclass
class Snippet:
    """A scored sentence-level passage extracted from a page."""
    page_id: int
    document_id: int
    page_number: int
    title: str
    snippet: str
    score: float

    def to_dict(self) -> dict:
        return {
            "page_id": self.page_id,
            "document_id": self.document_id,
            "page_number": self.page_number,
            "title": self.title,
            "snippet": self.snippet,
            "score": self.score,
        }


# ── Sentence Splitting ───────────────────────────────────────────────────────

# Regex to split on sentence boundaries (period, exclamation, question mark
# followed by space or end of string), while preserving abbreviations like "e.g."
_SENTENCE_RE = re.compile(
    r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])$',
)


def split_sentences(text: str) -> list[str]:
    """
    Split text into sentences.
    Falls back to newline splitting if regex produces too few results.
    """
    # First pass: regex sentence splitting
    sentences = _SENTENCE_RE.split(text.strip())

    # If we got very few sentences, try splitting by newlines
    if len(sentences) <= 1:
        sentences = [s.strip() for s in text.split("\n") if s.strip()]

    # Filter out very short fragments (less than 15 chars)
    sentences = [s for s in sentences if len(s.strip()) >= 15]

    return sentences


# ── Tokenization ──────────────────────────────────────────────────────────────

def tokenize(text: str) -> set[str]:
    """Simple word tokenizer: lowercase, alpha-only, 3+ chars."""
    return {w for w in re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())}


# ── Snippet Extraction ───────────────────────────────────────────────────────

def extract_snippets(
    query: str,
    pages: list[dict],
    top_n_per_page: int = 3,
) -> list[Snippet]:
    """
    Extract the most relevant snippets from a list of BM25-retrieved pages.

    Algorithm:
        1. Tokenize the query
        2. For each page, split content into sentences
        3. Score each sentence by:
           - overlap: count of query tokens found in the sentence (×2.0 weight)
           - tf_boost: sum of raw frequencies of query tokens in the sentence (×0.5 weight)
        4. Take top_n_per_page sentences per page
        5. Return all snippets sorted by score (descending)

    Args:
        query: The original user query
        pages: List of page dicts from BM25 search (must have page_id, document_id,
               content, page_number, title)
        top_n_per_page: Maximum snippets to extract per page

    Returns:
        List of Snippet objects sorted by score (descending)
    """
    query_tokens = tokenize(query)

    if not query_tokens:
        # If no valid tokens, return a snippet from each page (first sentence)
        snippets = []
        for page in pages:
            sents = split_sentences(page.get("content", ""))
            if sents:
                snippets.append(Snippet(
                    page_id=page["page_id"],
                    document_id=page["document_id"],
                    page_number=page.get("page_number", 0),
                    title=page.get("title", ""),
                    snippet=sents[0],
                    score=0.0,
                ))
        return snippets

    all_snippets: list[Snippet] = []

    for page in pages:
        content = page.get("content", "")
        sentences = split_sentences(content)

        if not sentences:
            continue

        # Score each sentence
        scored: list[tuple[str, float]] = []
        for sent in sentences:
            sent_tokens = tokenize(sent)
            sent_lower = sent.lower()

            # Overlap score: how many query tokens appear in the sentence
            overlap = len(query_tokens & sent_tokens)

            # TF boost: raw frequency of query terms in the sentence
            tf_boost = sum(sent_lower.count(t) for t in query_tokens)

            score = overlap * 2.0 + tf_boost * 0.5
            scored.append((sent, score))

        # Sort by score, take top N
        scored.sort(key=lambda x: x[1], reverse=True)

        for sent, score in scored[:top_n_per_page]:
            if score > 0:
                all_snippets.append(Snippet(
                    page_id=page["page_id"],
                    document_id=page["document_id"],
                    page_number=page.get("page_number", 0),
                    title=page.get("title", ""),
                    snippet=sent.strip(),
                    score=score,
                ))

    # Global sort by score
    all_snippets.sort(key=lambda s: s.score, reverse=True)

    return all_snippets
