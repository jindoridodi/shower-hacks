"""Pure entry point for Emily/Trista; no persistence or external calls."""
from .cleaner import clean_markdown
from .sensitivity import prepare_for_storage
from .chunker import chunk_text


def process_document(document: dict, *, max_chars: int = 1000,
                     confirmed_boilerplate: tuple[str, ...] = ()) -> dict:
    for field in ('document_id', 'source_id'):
        if not isinstance(document.get(field), str) or not document[field].strip():
            raise ValueError(f'{field} must be a nonempty string')
    checked = prepare_for_storage(document['raw_content'])
    cleaned = clean_markdown(checked['raw_content'], confirmed_boilerplate=confirmed_boilerplate) if checked['raw_content'] is not None else ''
    if not cleaned.strip():
        checked['sensitivity_status'] = ('needs_review' if checked['sensitivity_status'] == 'needs_review' else 'blocked')
        checked['raw_content'] = None
    return {**checked, 'document_id': document['document_id'],
            'source_id': document['source_id'], 'cleaned_text': cleaned,
            'chunks': chunk_text(cleaned, document_id=document['document_id'],
                                 source_id=document['source_id'],
                                 sensitivity_status=checked['sensitivity_status'],
                                 max_chars=max_chars)}
