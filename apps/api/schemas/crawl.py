from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CrawlStatus(StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class CrawlCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    source_id: str = Field(min_length=1)


class CrawlUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    status: CrawlStatus
    error_message: str | None = Field(default=None, max_length=4000)


class CrawlRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    status: str
    error_message: str | None
    started_at: str | None
    completed_at: str | None
    created_at: str
    updated_at: str
