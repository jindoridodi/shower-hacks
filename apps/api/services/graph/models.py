"""Public request model for Gephi exports."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from apps.api.services.discovery.models import CandidateSource


class GraphExportRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    query: str = Field(min_length=1, max_length=64)
    candidates: list[CandidateSource]
    provider_evidence: dict[str, list[str]] = Field(default_factory=dict, alias="providerEvidence")
