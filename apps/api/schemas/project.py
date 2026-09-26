from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)

    @field_validator("description")
    @classmethod
    def blank_description_is_null(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value or None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    created_at: str
    updated_at: str


class SensitivityStatus(StrEnum):
    unreviewed = "unreviewed"
    clear = "clear"
    sensitive = "sensitive"
    redacted = "redacted"
