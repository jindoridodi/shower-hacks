"""Public models and internal provider records for discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from apps.api.services.discovery.normalize import normalize_username, validate_public_url

Confidence = Literal["high", "medium", "low"]
QueryType = Literal["username", "url"]
ProviderName = Literal["sherlock", "maigret", "whatsmyname", "explicit_url", "user_supplied"]


class CandidateSource(BaseModel):
    """The stable contract consumed by the backend and frontend."""

    model_config = ConfigDict(populate_by_name=True)

    url: str
    platform: str
    candidate_username: str | None = Field(default=None, alias="candidateUsername")
    confidence: Confidence
    match_reason: str = Field(alias="matchReason")


class DiscoveryRequest(BaseModel):
    """Validated input for the discovery endpoint."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    query: str = Field(min_length=1, max_length=512)
    query_type: QueryType = Field(default="username", alias="queryType")
    project_id: str | None = Field(default=None, alias="projectId", min_length=1, max_length=128)
    limit: int = Field(default=25, ge=1, le=100)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query must not be empty")
        return value

    @model_validator(mode="before")
    @classmethod
    def infer_query_type(cls, value: object) -> object:
        """Keep legacy queryType support while making input type automatic."""

        if not isinstance(value, dict) or "queryType" in value:
            return value
        query = str(value.get("query", "")).strip()
        parsed = urlsplit(query)
        if parsed.scheme or "://" in query:
            return {**value, "queryType": "url"}
        return value

    @model_validator(mode="after")
    def validate_query_and_providers(self) -> "DiscoveryRequest":
        if self.query_type == "username":
            normalize_username(self.query)
        else:
            validate_public_url(self.query)
        return self


class DiscoveryResponse(BaseModel):
    """Stable endpoint response with graceful provider failures."""

    model_config = ConfigDict(populate_by_name=True)

    query: str
    candidates: list[CandidateSource]
    providers_used: list[str] = Field(alias="providersUsed")
    provider_evidence: dict[str, list[str]] = Field(default_factory=dict, alias="providerEvidence")
    saved_sources: list["SavedSource"] = Field(default_factory=list, alias="savedSources")
    partial: bool
    warnings: list[str]


@dataclass(frozen=True)
class ProviderRecord:
    """Tool-neutral discovery record before normalization and scoring."""

    url: str
    platform: str | None
    candidate_username: str | None
    exact_username_match: bool
    provider: str
    match_reason: str
    direct_input: bool = False


@dataclass
class ProviderResult:
    """Provider output that can represent partial success."""

    provider: str
    records: list[ProviderRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    partial: bool = False


class ProviderError(RuntimeError):
    """A non-fatal provider failure exposed as a response warning."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class SavedSource(BaseModel):
    """A project-scoped, user-supplied candidate URL."""

    model_config = ConfigDict(populate_by_name=True)

    source_id: str = Field(alias="sourceId")
    project_id: str = Field(alias="projectId")
    username: str
    url: str
    platform: str
    confidence: Confidence = "high"
    match_reason: str = Field(
        default="User-supplied public URL attached to this project and username.",
        alias="matchReason",
    )
    created_at: str = Field(alias="createdAt")
