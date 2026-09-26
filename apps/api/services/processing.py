"""Pure entry point for Emily/Trista; no persistence or external calls."""
from .cleaner import clean_markdown
from .sensitivity import prepare_for_storage, filter_metadata
from .chunker import chunk_text


def process_document(document: dict, *, max_chars: int = 1000,
                     confirmed_boilerplate: tuple[str, ...] = ()) -> dict:
    """Use a caller-supplied database document ID; never generate or query IDs."""
    if not isinstance(document, dict):
        raise TypeError('document must be a dictionary')
    document_id = document.get('document_id')
    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError('document_id must be a nonempty database ID')
    for field in ('source_id',):
        if not isinstance(document.get(field), str) or not document[field].strip():
            raise ValueError(f'{field} must be a nonempty string')
    if 'raw_text' not in document:
        raise ValueError('raw_text is required')
    checked = prepare_document(document['raw_text'], metadata=document.get('metadata'),
                               confirmed_boilerplate=confirmed_boilerplate)
    cleaned = checked['cleaned_text']
    return {**checked, 'document_id': document_id,
            'source_id': document['source_id'], 'cleaned_text': cleaned,
            'chunks': chunk_text(cleaned, document_id=document_id,
                                 source_id=document['source_id'],
                                 sensitivity_status=checked['sensitivity_status'],
                                 max_chars=max_chars)}


def prepare_document(raw_text: str, *, metadata: dict | None = None,
                     confirmed_boilerplate: tuple[str, ...] = ()) -> dict:
    """Filter and clean before persistence, without allocating a document ID."""
    metadata = filter_metadata(metadata)
    checked = prepare_for_storage(raw_text)
    if metadata['metadata_findings']:
        checked['sensitivity_status'] = 'redacted'
    cleaned = clean_markdown(checked['raw_text'], confirmed_boilerplate=confirmed_boilerplate) if checked['raw_text'] is not None else ''
    if not cleaned.strip():
        checked['raw_text'] = None
    return {**checked, **metadata, 'cleaned_text': cleaned}
