"""
Document parsers for PDF, DOCX, TXT, Markdown, and HTML files.
Each parser returns a list of PageData dicts representing logical pages.
"""
import re
import os
from dataclasses import dataclass, field, asdict


@dataclass
class PageData:
    """A single extracted page/section from a document."""
    page_number: int
    content: str
    title: str = ""
    section_heading: str = ""
    keywords: str = ""
    token_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


# ── Keyword Extraction ────────────────────────────────────────────────────────

# Common English stop words to exclude from keyword extraction
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "and", "but", "or", "if", "while", "because", "until", "that", "this",
    "these", "those", "it", "its", "he", "she", "they", "them", "his",
    "her", "their", "what", "which", "who", "whom", "my", "your", "we",
    "our", "i", "me", "us", "you", "just", "also", "about", "up",
}


def extract_keywords(text: str, top_n: int = 10) -> str:
    """Extract top keywords from text using simple term frequency analysis."""
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    freq = {}
    for w in words:
        if w not in STOP_WORDS:
            freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq, key=freq.get, reverse=True)
    return ", ".join(sorted_words[:top_n])


def estimate_tokens(text: str) -> int:
    """Approximate token count: words × 1.3 (suitable for local models)."""
    return int(len(text.split()) * 1.3)


# ── PDF Parser ────────────────────────────────────────────────────────────────

class PDFParser:
    """Extract text per physical page from PDF files using PyMuPDF."""

    @staticmethod
    def parse(file_path: str) -> list[PageData]:
        import fitz  # PyMuPDF
        pages = []
        doc = fitz.open(file_path)

        # Try to get document title from metadata
        doc_title = doc.metadata.get("title", "") or ""

        for i, page in enumerate(doc):
            text = page.get_text("text").strip()
            if not text:
                continue

            # Extract first line as potential section heading
            lines = text.split("\n")
            heading = lines[0].strip() if lines else ""

            pages.append(PageData(
                page_number=i + 1,
                content=text,
                title=doc_title,
                section_heading=heading[:200],
                keywords=extract_keywords(text),
                token_count=estimate_tokens(text),
            ))

        doc.close()
        return pages


# ── DOCX Parser ───────────────────────────────────────────────────────────────

class DOCXParser:
    """Extract text from DOCX files, split by page breaks or paragraph groups."""

    PARAGRAPHS_PER_PAGE = 20  # fallback if no page breaks

    @staticmethod
    def parse(file_path: str) -> list[PageData]:
        from docx import Document
        doc = Document(file_path)

        # Collect all paragraph texts
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append({
                    "text": text,
                    "style": para.style.name if para.style else "",
                })

        if not paragraphs:
            return []

        # Try to find title from first heading
        doc_title = ""
        for p in paragraphs:
            if "heading" in p["style"].lower() or "title" in p["style"].lower():
                doc_title = p["text"]
                break

        # Split into pages by paragraph count
        pages = []
        chunk_size = DOCXParser.PARAGRAPHS_PER_PAGE
        for i in range(0, len(paragraphs), chunk_size):
            chunk = paragraphs[i:i + chunk_size]
            content = "\n".join(p["text"] for p in chunk)

            # Find section heading in this chunk
            heading = ""
            for p in chunk:
                if "heading" in p["style"].lower():
                    heading = p["text"]
                    break

            pages.append(PageData(
                page_number=(i // chunk_size) + 1,
                content=content,
                title=doc_title,
                section_heading=heading[:200],
                keywords=extract_keywords(content),
                token_count=estimate_tokens(content),
            ))

        return pages


# ── TXT Parser ────────────────────────────────────────────────────────────────

class TXTParser:
    """Split plain text files into pages by line count (~60 lines/page)."""

    LINES_PER_PAGE = 60

    @staticmethod
    def parse(file_path: str) -> list[PageData]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()

        if not all_lines:
            return []

        # Use first non-empty line as title
        doc_title = ""
        for line in all_lines:
            if line.strip():
                doc_title = line.strip()[:200]
                break

        pages = []
        chunk_size = TXTParser.LINES_PER_PAGE
        for i in range(0, len(all_lines), chunk_size):
            chunk = all_lines[i:i + chunk_size]
            content = "".join(chunk).strip()
            if not content:
                continue

            pages.append(PageData(
                page_number=(i // chunk_size) + 1,
                content=content,
                title=doc_title,
                section_heading="",
                keywords=extract_keywords(content),
                token_count=estimate_tokens(content),
            ))

        return pages


# ── Markdown Parser ───────────────────────────────────────────────────────────

class MarkdownParser:
    """Split Markdown files by headings (# or ##)."""

    @staticmethod
    def parse(file_path: str) -> list[PageData]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()

        if not text.strip():
            return []

        # Split by top-level headings (# or ##)
        sections = re.split(r'^(#{1,2}\s+.+)$', text, flags=re.MULTILINE)

        # Reassemble: pair headings with their content
        pages = []
        doc_title = ""
        current_heading = ""
        current_content = ""
        page_num = 0

        for part in sections:
            part = part.strip()
            if not part:
                continue

            if re.match(r'^#{1,2}\s+', part):
                # Save previous section if exists
                if current_content.strip():
                    page_num += 1
                    pages.append(PageData(
                        page_number=page_num,
                        content=current_content.strip(),
                        title=doc_title,
                        section_heading=current_heading[:200],
                        keywords=extract_keywords(current_content),
                        token_count=estimate_tokens(current_content),
                    ))

                current_heading = re.sub(r'^#{1,2}\s+', '', part)
                if not doc_title:
                    doc_title = current_heading
                current_content = part + "\n"
            else:
                current_content += part + "\n"

        # Last section
        if current_content.strip():
            page_num += 1
            pages.append(PageData(
                page_number=page_num,
                content=current_content.strip(),
                title=doc_title,
                section_heading=current_heading[:200],
                keywords=extract_keywords(current_content),
                token_count=estimate_tokens(current_content),
            ))

        # Handle files with no headings
        if not pages and text.strip():
            pages.append(PageData(
                page_number=1,
                content=text.strip(),
                title=text.strip().split("\n")[0][:200],
                section_heading="",
                keywords=extract_keywords(text),
                token_count=estimate_tokens(text),
            ))

        return pages


# ── HTML Parser ───────────────────────────────────────────────────────────────

class HTMLParser:
    """Split HTML files by section/heading tags."""

    @staticmethod
    def parse(file_path: str) -> list[PageData]:
        from bs4 import BeautifulSoup

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            html = f.read()

        soup = BeautifulSoup(html, "lxml")

        # Remove script and style elements
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Try to get title
        doc_title = ""
        title_tag = soup.find("title")
        if title_tag:
            doc_title = title_tag.get_text(strip=True)

        # Split by sections or headings
        sections = soup.find_all(["section", "article", "h1", "h2", "h3"])

        if sections:
            pages = []
            page_num = 0
            for section in sections:
                content = section.get_text(separator="\n", strip=True)
                if not content or len(content) < 20:
                    continue

                heading = ""
                h_tag = section.find(["h1", "h2", "h3"])
                if h_tag:
                    heading = h_tag.get_text(strip=True)
                elif section.name in ["h1", "h2", "h3"]:
                    heading = content.split("\n")[0]

                page_num += 1
                pages.append(PageData(
                    page_number=page_num,
                    content=content,
                    title=doc_title,
                    section_heading=heading[:200],
                    keywords=extract_keywords(content),
                    token_count=estimate_tokens(content),
                ))

            if pages:
                return pages

        # Fallback: treat entire body as one page
        body = soup.find("body")
        text = body.get_text(separator="\n", strip=True) if body else soup.get_text(separator="\n", strip=True)
        if text.strip():
            return [PageData(
                page_number=1,
                content=text.strip(),
                title=doc_title,
                section_heading="",
                keywords=extract_keywords(text),
                token_count=estimate_tokens(text),
            )]

        return []


# ── Parser Registry ───────────────────────────────────────────────────────────

PARSERS = {
    ".pdf": PDFParser,
    ".docx": DOCXParser,
    ".txt": TXTParser,
    ".md": MarkdownParser,
    ".markdown": MarkdownParser,
    ".html": HTMLParser,
    ".htm": HTMLParser,
}

SUPPORTED_EXTENSIONS = set(PARSERS.keys())


def get_parser(file_path: str):
    """Return the appropriate parser class for a file, or None if unsupported."""
    ext = os.path.splitext(file_path)[1].lower()
    return PARSERS.get(ext)
