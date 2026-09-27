from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any


_MONTH_DATE = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b"
)
_ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_AMBIGUOUS_NUMERIC_DATE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b")
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_SENTENCE = re.compile(r"[^.!?]+[.!?]?")


def extract_timeline_items(evidence_excerpts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    extracted_items = []

    for excerpt in evidence_excerpts:
        if excerpt.get("sensitivityStatus") != "safe":
            continue

        source_id = excerpt.get("sourceId")
        text = excerpt.get("text")
        if not isinstance(source_id, str) or not isinstance(text, str):
            continue

        extracted_items.extend(_extract_from_text(source_id, text))

    extracted_items.sort(key=lambda item: item[0])
    return [item for _, item in extracted_items]


def _extract_from_text(source_id: str, text: str) -> list[tuple[str, dict[str, Any]]]:
    matches: list[tuple[re.Match[str], str]] = []
    matches.extend((match, "month") for match in _MONTH_DATE.finditer(text))
    matches.extend((match, "iso") for match in _ISO_DATE.finditer(text))
    matches.extend((match, "ambiguous") for match in _AMBIGUOUS_NUMERIC_DATE.finditer(text))

    covered_positions = [match.span() for match, _ in matches]
    matches.extend(
        (match, "year")
        for match in _YEAR.finditer(text)
        if not any(start <= match.start() and match.end() <= end for start, end in covered_positions)
    )

    items = []
    for match, match_type in sorted(matches, key=lambda item: item[0].start()):
        date_text = match.group()
        normalized_date = _normalized_date(date_text, match_type)
        item = {
            "dateText": date_text,
            "eventText": _event_text(text, match.start()),
            "sourceId": source_id,
            "confidence": _confidence(match_type),
        }
        if normalized_date:
            item["normalizedDate"] = normalized_date
        items.append((_sort_key(date_text, normalized_date, match_type), item))

    return items


def _normalized_date(date_text: str, match_type: str) -> str | None:
    try:
        if match_type == "month":
            return datetime.strptime(date_text, "%B %d, %Y").date().isoformat()
        if match_type == "iso":
            return date.fromisoformat(date_text).isoformat()
    except ValueError:
        return None
    return None


def _event_text(text: str, position: int) -> str:
    for sentence in _SENTENCE.finditer(text):
        if sentence.start() <= position < sentence.end():
            return sentence.group().strip()
    return text.strip()


def _sort_key(date_text: str, normalized_date: str | None, match_type: str) -> str:
    if normalized_date:
        return normalized_date
    if match_type == "year":
        return f"{date_text}-00-00"
    return "9999-99-99"


def _confidence(match_type: str) -> float:
    if match_type in {"month", "iso"}:
        return 0.95
    if match_type == "year":
        return 0.75
    return 0.5
