from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from apps.api.schemas.document import ChunkRead
from apps.api.schemas.source import SourceRead
from apps.api.services.report_persistence import EvidenceExcerpt, GeneratedClaim, GeneratedReport


class EvidenceExcerptIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    source_id: str = Field(alias="sourceId", min_length=1)
    text: str = Field(min_length=1, max_length=8000)
    sensitivity_status: str = Field(alias="sensitivityStatus", min_length=1)


class GeneratedClaimIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=8000)
    claim_type: Literal["observed", "inferred", "uncertain", "unknown"] = Field(alias="claimType")
    source_ids: list[str] = Field(default_factory=list, alias="sourceIds")


class GeneratedReportIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore", str_strip_whitespace=True)

    id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=300)
    claims: list[GeneratedClaimIn] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


class PersistReportRequest(BaseModel):
    report: GeneratedReportIn
    evidence: list[EvidenceExcerptIn] = Field(default_factory=list)

    def to_models(self) -> tuple[GeneratedReport, list[EvidenceExcerpt]]:
        report = GeneratedReport(
            id=self.report.id,
            title=self.report.title,
            claims=tuple(
                GeneratedClaim(
                    id=claim.id,
                    text=claim.text,
                    claim_type=claim.claim_type,
                    source_ids=tuple(claim.source_ids),
                )
                for claim in self.report.claims
            ),
            unknowns=tuple(self.report.unknowns),
        )
        evidence = [
            EvidenceExcerpt(
                source_id=item.source_id,
                text=item.text,
                sensitivity_status=item.sensitivity_status,
            )
            for item in self.evidence
        ]
        return report, evidence


class CorpusDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    content_hash: str
    title: str | None
    sensitivity_status: str
    chunks: list[ChunkRead]


class CorpusRead(BaseModel):
    project_id: str
    sources: list[SourceRead]
    documents: list[CorpusDocumentRead]
