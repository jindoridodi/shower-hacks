"""Lossless slices of filtered Markdown, with offsets into cleaned_text only."""
import re


def chunk_text(text: str, *, document_id: str, source_id: str,
               sensitivity_status: str, max_chars: int = 1000) -> list[dict]:
    if max_chars < 1:
        raise ValueError('max_chars must be positive')
    if sensitivity_status not in {'approved', 'redacted'} or not text.strip():
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            window = text[start:end]
            breaks = list(re.finditer(r'\n\s*\n|\n(?=#{1,6} )', window))
            if breaks:
                end = start + breaks[-1].end()
            else:
                spaces = list(re.finditer(r'\s+', window))
                if spaces:
                    end = start + spaces[-1].end()
        # Attach separator-only tails so no characters disappear.
        if not text[end:].strip():
            end = len(text)
        piece = text[start:end]
        if not piece.strip() and chunks:
            chunks[-1]['text'] += piece
            chunks[-1]['fts_text'] += piece
            chunks[-1]['end_char'] = end
        elif piece.strip():
            chunks.append({'chunk_index': len(chunks), 'document_id': document_id,
                           'source_id': source_id, 'text': piece, 'fts_text': piece,
                           'start_char': start, 'end_char': end,
                           'evidence_basis': 'filtered_text'})
        else:
            # Leading whitespace stays with the first non-empty chunk.
            next_nonspace = re.search(r'\S', text[end:])
            if next_nonspace:
                end += next_nonspace.start() + 1
                piece = text[start:end]
                chunks.append({'chunk_index': 0, 'document_id': document_id,
                               'source_id': source_id, 'text': piece, 'fts_text': piece,
                               'start_char': start, 'end_char': end,
                               'evidence_basis': 'filtered_text'})
        start = end
    return chunks
