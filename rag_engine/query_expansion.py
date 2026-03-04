"""
Query expansion module.
Improves retrieval recall by adding synonyms and applying stemming.
"""
import re
from whoosh.analysis import StemmingAnalyzer


# ── Synonym Groups ────────────────────────────────────────────────────────────
# Curated synonym maps for common technical and general concepts.
# When any word in a group is found in the query, all related terms are added.

SYNONYM_GROUPS = {
    "authentication": ["login", "credentials", "identity", "authorization", "auth", "signin", "signon"],
    "error": ["exception", "failure", "fault", "bug", "crash", "issue", "problem"],
    "performance": ["speed", "latency", "throughput", "optimization", "benchmark", "fast", "slow"],
    "database": ["db", "storage", "datastore", "repository", "sql", "table", "schema"],
    "api": ["endpoint", "interface", "service", "rest", "graphql", "route"],
    "user": ["account", "profile", "member", "client"],
    "security": ["encryption", "ssl", "tls", "firewall", "vulnerability", "protection"],
    "configuration": ["config", "settings", "preferences", "options", "parameters"],
    "deployment": ["deploy", "release", "publish", "staging", "production", "ci", "cd"],
    "testing": ["test", "unit", "integration", "qa", "assertion", "mock", "coverage"],
    "network": ["http", "tcp", "socket", "connection", "request", "response", "dns"],
    "file": ["document", "upload", "download", "attachment", "resource"],
    "search": ["find", "query", "lookup", "filter", "index", "retrieve"],
    "install": ["setup", "installation", "configure", "initialize", "bootstrap"],
    "delete": ["remove", "drop", "destroy", "purge", "clean"],
    "create": ["add", "new", "generate", "build", "make", "insert"],
    "update": ["modify", "change", "edit", "alter", "patch"],
}

# Build reverse lookup: word → group key
_WORD_TO_GROUP: dict[str, str] = {}
for key, syns in SYNONYM_GROUPS.items():
    _WORD_TO_GROUP[key] = key
    for s in syns:
        _WORD_TO_GROUP[s] = key

# Shared stemming analyzer instance
_analyzer = StemmingAnalyzer()


def expand_query(query: str) -> str:
    """
    Expand a user query with:
    1. Stemmed tokens (via Whoosh's StemmingAnalyzer)
    2. Synonym expansion from curated groups

    Example:
        "authentication system" → "authent system login credentials identity authorization auth signin signon"
    """
    # Step 1: Get stemmed tokens
    stemmed = [t.text for t in _analyzer(query)]

    # Step 2: Add synonyms for original words
    expanded = set(stemmed)
    for word in query.lower().split():
        clean = re.sub(r'[^\w]', '', word)
        if not clean:
            continue

        group_key = _WORD_TO_GROUP.get(clean)
        if group_key:
            expanded.add(group_key)
            expanded.update(SYNONYM_GROUPS[group_key])

    return " ".join(expanded)
