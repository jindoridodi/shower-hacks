from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.clock import utc_now
from apps.api.db import transaction
from apps.api.errors import APIError
from apps.api.models import Source, SourceApproval
from apps.api.schemas.approval import CandidateApprovalCreate, CandidateApprovalRead
from apps.api.services.discovery.normalize import normalize_url
from apps.api.services.projects import get_project
from apps.api.services.urls import InvalidURL, canonicalize_url


def approve_candidate(db: Session, payload: CandidateApprovalCreate) -> CandidateApprovalRead:
    get_project(db, payload.project_id)
    try:
        approved_url = normalize_url(payload.candidate.url)
        canonical_url = canonicalize_url(approved_url)
    except (InvalidURL, ValueError) as error:
        raise APIError(422, "invalid_url", str(error)) from error

    existing = db.scalar(
        select(Source).where(
            Source.project_id == payload.project_id,
            Source.canonical_url == canonical_url,
        )
    )
    if existing is not None:
        raise APIError(
            409,
            "duplicate_canonical_url",
            f"A source with canonical URL {canonical_url} already exists in this project",
            existing_id=existing.id,
        )

    now = utc_now()
    source = Source(
        id=str(uuid4()),
        project_id=payload.project_id,
        url=approved_url,
        canonical_url=canonical_url,
        status="pending",
        created_at=now,
        updated_at=now,
    )
    provider_evidence = list(dict.fromkeys(payload.provider_evidence))
    approval = SourceApproval(
        id=str(uuid4()),
        source_id=source.id,
        target_username=payload.username,
        platform=payload.candidate.platform,
        confidence=payload.candidate.confidence,
        match_reason=payload.candidate.match_reason,
        provider_evidence=json.dumps(provider_evidence),
        approved_at=now,
    )
    with transaction(db):
        db.add(source)
        db.add(approval)
    return CandidateApprovalRead(
        sourceId=source.id,
        projectId=source.project_id,
        url=source.url,
        canonicalUrl=source.canonical_url,
        status="pending",
        username=approval.target_username,
        platform=approval.platform,
        confidence=approval.confidence,
        matchReason=approval.match_reason,
        providerEvidence=provider_evidence,
        approvedAt=approval.approved_at,
    )


def list_approvals(db: Session, project_id: str) -> list[CandidateApprovalRead]:
    get_project(db, project_id)
    rows = db.execute(
        select(Source, SourceApproval)
        .join(SourceApproval, SourceApproval.source_id == Source.id)
        .where(Source.project_id == project_id)
        .order_by(SourceApproval.approved_at, SourceApproval.id)
    ).all()
    return [
        CandidateApprovalRead(
            sourceId=source.id,
            projectId=source.project_id,
            url=source.url,
            canonicalUrl=source.canonical_url,
            status=source.status,
            username=approval.target_username,
            platform=approval.platform,
            confidence=approval.confidence,
            matchReason=approval.match_reason,
            providerEvidence=json.loads(approval.provider_evidence),
            approvedAt=approval.approved_at,
        )
        for source, approval in rows
    ]
