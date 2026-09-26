"""Models for projects and manually attached public sources."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from apps.api.services.discovery.models import SavedSource
from apps.api.services.discovery.normalize import normalize_username, validate_public_url


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("project name must not be empty")
        return value


class Project(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str = Field(alias="projectId")
    name: str
    created_at: str = Field(alias="createdAt")


class ManualSourceCreateRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    url: str = Field(min_length=1, max_length=2048)

    @field_validator("username")
    @classmethod
    def normalize_username_value(cls, value: str) -> str:
        return normalize_username(value)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        value = value.strip()
        validate_public_url(value)
        return value


class ManualSourceList(BaseModel):
    sources: list[SavedSource]
