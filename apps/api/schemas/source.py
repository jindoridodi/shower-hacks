from pydantic import BaseModel, ConfigDict, Field


class SourceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    project_id: str = Field(min_length=1)
    url: str = Field(min_length=1, max_length=2000)


class ProjectSourceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    url: str = Field(min_length=1, max_length=2000)


class SourceApprovalUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    approval_status: str = Field(pattern="^(approved|rejected)$")


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    url: str
    canonical_url: str
    status: str
    approval_status: str
    is_allowlisted: bool
    approved_at: str | None
    approval_origin: str | None
    content_hash: str | None
    scraped_at: str | None
    created_at: str
    updated_at: str
