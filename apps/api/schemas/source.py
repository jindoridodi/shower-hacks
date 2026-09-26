from pydantic import BaseModel, ConfigDict, Field


class SourceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    project_id: str = Field(min_length=1)
    url: str = Field(min_length=1, max_length=2000)


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    url: str
    canonical_url: str
    status: str
    content_hash: str | None
    scraped_at: str | None
    created_at: str
    updated_at: str
