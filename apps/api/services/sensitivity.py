"""Bounded English-language heuristics. Approval is not a privacy guarantee."""
from dataclasses import dataclass, asdict
import html
import re
from urllib.parse import unquote


@dataclass(frozen=True)
class Finding:
    category: str
    # No source spans, values, or excerpts are returned or logged.


# !?!?!?!?
PATTERNS = {
    'email': r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',
    'phone': r'(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)',
    'credential': r'(?i)(?:password|passwd|api[_ -]?key|access[_ -]?token|secret)\s*["\']?\s*[:=]\s*\S+|\bBearer\s+\S+|\b(?:sk-|ghp_)[A-Za-z0-9_-]{12,}|-----BEGIN [A-Z ]*PRIVATE KEY-----',
    'financial_identifier': r'(?i)\b(?:IBAN|routing number|bank account|credit card|ssn)\b\s*[:=]?\s*[A-Z0-9 -]*\d',
    'health_context': r'(?i)\b(?:diagnosed|diagnosis|patient|my medication|her medication|his medication|suffers from)\b',
    'finance_context': r'(?i)\b(?:my|his|her|their)\s+(?:salary|debt|income|balance)\b',
    'private_location': r'(?i)\b(?:home address|lives at|live at|gps|latitude|longitude)\b|[+-]?\d{1,3}\.\d{4,}\s*,\s*[+-]?\d{1,3}\.\d{4,}',
    'ambiguous_contact': r'(?i)\b\w+\s*\[at\]\s*\w+|\b(?:password|api[_ -]?key|access[_ -]?token)\b',
}
# Detection and policy are deliberately separate.
POLICY = {
    'email': 'redacted', 'phone': 'redacted',
    'credential': 'blocked', 'financial_identifier': 'blocked',
    'health_context': 'needs_review', 'finance_context': 'needs_review',
    'private_location': 'needs_review', 'ambiguous_contact': 'needs_review',
}


def detect_sensitive(text: str) -> list[Finding]:
    """Inspect literal, HTML-escaped and percent-encoded Markdown destinations too."""
    decoded = text
    for _ in range(3):
        decoded = html.unescape(unquote(decoded)) # % decode -> html entity decode
    return [Finding(kind) for kind, pattern in PATTERNS.items()
            if re.search(pattern, decoded)]


def prepare_for_storage(raw_content: str) -> dict:
    """Run BEFORE any persistence/logging. None means do not store the content.

    Contact-bearing paragraphs are removed wholesale, including link destinations.
    Contextual candidates withhold the entire document pending review.
    """
    if not isinstance(raw_content, str):
        raise TypeError('raw_content must be a string')
    findings = detect_sensitive(raw_content)
    categories = {f.category for f in findings}
    actions = {POLICY[c] for c in categories}
    if 'blocked' in actions:
        status, safe = 'blocked', None
    elif 'needs_review' in actions:
        status, safe = 'needs_review', None
    else:
        normalized = raw_content.replace('\r\n', '\n').replace('\r', '\n')
        # Whole blocks also avoid leaving table headers or reference-link labels
        # attached to a removed contact value in the same paragraph.
        blocks = re.split(r'\n[ \t]*\n', normalized)
        safe = '\n\n'.join(block for block in blocks if not detect_sensitive(block))
        status = 'redacted' if findings else 'approved'
        if not safe.strip():
            status, safe = 'blocked', None
    return {'raw_content': safe, 'sensitivity_status': status,
            'findings': [asdict(f) for f in findings]}
