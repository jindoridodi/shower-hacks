from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from apps.api.services.discovery.models import CandidateSource, ProviderName
from apps.api.services.discovery.normalize import normalize_username


class CandidateApprovalCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(alias="projectId", min_length=1)
    username: str = Field(min_length=1, max_length=64)
    candidate: CandidateSource
    provider_evidence: list[ProviderName] = Field(alias="providerEvidence", min_length=1, max_length=4)

    @field_validator("username")
    @classmethod
    def normalize_username_value(cls, value: str) -> str:
        return normalize_username(value)

    @model_validator(mode="after")
    def candidate_username_matches(self) -> "CandidateApprovalCreate":
        if self.candidate.candidate_username and normalize_username(self.candidate.candidate_username) != self.username:
            raise ValueError("candidateUsername must match username")
        return self


class CandidateApprovalRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_id: str = Field(alias="sourceId")
    project_id: str = Field(alias="projectId")
    url: str
    canonical_url: str = Field(alias="canonicalUrl")
    status: str
    username: str
    platform: str
    confidence: Literal["high", "medium", "low"]
    match_reason: str = Field(alias="matchReason")
    provider_evidence: list[ProviderName] = Field(alias="providerEvidence")
    approved_at: str = Field(alias="approvedAt")
