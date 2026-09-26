"""Bounded English-language heuristics. Approval is not a privacy guarantee."""
from dataclasses import dataclass, asdict
import html
import re
from urllib.parse import unquote, urlsplit, parse_qsl


@dataclass(frozen=True)
class Finding:
    category: str
    # No source spans, values, or excerpts are returned or logged.


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
    'email': 'remove_block', 'phone': 'remove_block',
    'credential': 'remove_block', 'financial_identifier': 'remove_block',
    'health_context': 'remove_block', 'finance_context': 'remove_block',
    'private_location': 'remove_block', 'ambiguous_contact': 'remove_block',
}


def detect_sensitive(text: str) -> list[Finding]:
    """Inspect literal, HTML-escaped and percent-encoded Markdown destinations too."""
    decoded = text
    for _ in range(3):
        decoded = html.unescape(unquote(decoded)) # % decode -> html entity decode
    return [Finding(kind) for kind, pattern in PATTERNS.items()
            if re.search(pattern, decoded)]


def prepare_for_storage(raw_text: str) -> dict:
    """Run BEFORE any persistence/logging. None means do not store the content.

    Paragraphs with any detected category are removed, including link destinations.
    Blocks are separated by blank lines; unaffected blocks are retained.
    unreviewed is reserved for inputs that have not been inspected.
    """
    if not isinstance(raw_text, str):
        raise TypeError('raw_text must be a string')
    normalized = raw_text.replace('\r\n', '\n').replace('\r', '\n')
    blocks = re.split(r'\n[ \t]*\n', normalized)
    kept = []
    categories = set()
    for block in blocks:
        findings = detect_sensitive(block)
        categories.update(f.category for f in findings)
        if not any(POLICY[f.category] == 'remove_block' for f in findings):
            kept.append(block)
    safe = '\n\n'.join(kept)
    status = 'redacted' if categories else 'clear'
    if not safe.strip():
        safe = None
    findings = [Finding(category) for category in PATTERNS if category in categories]
    return {'raw_text': safe, 'sensitivity_status': status,
            'findings': [asdict(f) for f in findings]}


def filter_metadata(metadata: dict | None) -> dict:
    """Keep inspected url/title values verbatim; omit a whole unsafe value.

    Other keys are not part of the metadata storage contract. Findings contain
    only field/category labels, never input values. This is not URL authorization.
    """
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise TypeError('metadata must be a dictionary')
    safe = {}
    findings = []
    for field in ('url', 'title'):
        value = metadata.get(field)
        if value is None:
            continue
        if not isinstance(value, str):
            raise TypeError(f'metadata.{field} must be a string')
        if not value.strip():
            continue
        categories = {f.category for f in detect_sensitive(value)}
        if field == 'url':
            try:
                parsed = urlsplit(value)
                if parsed.scheme not in {'http', 'https'} or not parsed.hostname or any(c.isspace() for c in value):
                    categories.add('invalid_url')
                if parsed.username is not None or parsed.password is not None:
                    categories.add('url_credentials')
                # Query names can identify secrets whose values lack a known prefix.
                for key, _ in parse_qsl(parsed.query) + parse_qsl(parsed.fragment):
                    if re.search(r'(?i)(token|secret|password|api.?key|authorization|signature|credential)', key):
                        categories.add('url_secret')
            except ValueError:
                categories.add('invalid_url')
        if categories:
            findings.extend({'field': field, 'category': c} for c in sorted(categories))
        else:
            safe[field] = value
    return {'metadata': safe, 'metadata_findings': findings}
