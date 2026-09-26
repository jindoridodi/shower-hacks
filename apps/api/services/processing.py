"""Pure entry point for Emily/Trista; no persistence or external calls."""
from uuid import uuid4

from .cleaner import clean_markdown
from .sensitivity import prepare_for_storage
from .chunker import chunk_text


def process_document(document: dict, *, max_chars: int = 1000,
                     confirmed_boilerplate: tuple[str, ...] = ()) -> dict:
    """Generate a UUID when document_id is omitted or None; preserve supplied IDs."""
    document_id = document.get('document_id')
    if document_id is None:
        document_id = str(uuid4())
    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError('document_id must be a nonempty string')
    for field in ('source_id',):
        if not isinstance(document.get(field), str) or not document[field].strip():
            raise ValueError(f'{field} must be a nonempty string')
    checked = prepare_for_storage(document['raw_text'])
    cleaned = clean_markdown(checked['raw_text'], confirmed_boilerplate=confirmed_boilerplate) if checked['raw_text'] is not None else ''
    if not cleaned.strip():
        checked['raw_text'] = None
    return {**checked, 'document_id': document_id,
            'source_id': document['source_id'], 'cleaned_text': cleaned,
            'chunks': chunk_text(cleaned, document_id=document_id,
                                 source_id=document['source_id'],
                                 sensitivity_status=checked['sensitivity_status'],
                                 max_chars=max_chars)}
