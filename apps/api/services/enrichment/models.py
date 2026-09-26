"""SpiderFoot enrichment boundary models."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from apps.api.services.discovery.models import Confidence
from apps.api.services.discovery.normalize import validate_public_url

TargetType = Literal["url", "username", "domain"]
EnrichmentModule = Literal["account_discovery", "public_metadata", "domain_provenance"]


class SpiderFootStartRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    target: str = Field(min_length=1, max_length=512)
    target_type: TargetType = Field(alias="targetType")
    modules: list[EnrichmentModule] = Field(min_length=1, max_length=3)

    @field_validator("target")
    @classmethod
    def clean_target(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("target must not be empty")
        return value

    @model_validator(mode="after")
    def validate_target(self) -> "SpiderFootStartRequest":
        if self.target_type == "url":
            validate_public_url(self.target)
        elif self.target_type == "username":
            if len(self.target) > 64 or not re.fullmatch(r"[A-Za-z0-9._-]+", self.target):
                raise ValueError("username contains unsupported characters")
        elif not re.fullmatch(r"(?=.{1,253}$)(?:[A-Za-z0-9-]{1,63}\.)+[A-Za-z]{2,63}", self.target):
            raise ValueError("domain is invalid")
        return self


class SpiderFootStartResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    job_id: str = Field(alias="jobId")
    status: str
    modules: list[str]


class EnrichmentFinding(BaseModel):
    type: Literal["public_url"]
    value: str
    source: Literal["spiderfoot"]
    module: str
    confidence: Confidence


class SpiderFootStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    job_id: str = Field(alias="jobId")
    status: str
    target: str
    findings: list[EnrichmentFinding]
    warnings: list[str] = Field(default_factory=list)
