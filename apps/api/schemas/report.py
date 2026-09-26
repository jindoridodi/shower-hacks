from pydantic import BaseModel, ConfigDict, Field


class ClaimSourceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    source_id: str = Field(min_length=1)
    excerpt: str = Field(min_length=1, max_length=8000)


class ClaimCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    claim_text: str = Field(min_length=1, max_length=8000)
    sources: list[ClaimSourceCreate] = Field(default_factory=list)


class ReportCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    project_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=300)


class ClaimSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    claim_id: str
    source_id: str
    excerpt: str
    created_at: str


class ClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    report_id: str
    claim_text: str
    position: int
    created_at: str
    sources: list[ClaimSourceRead]


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    title: str
    created_at: str
    updated_at: str
    claims: list[ClaimRead]
