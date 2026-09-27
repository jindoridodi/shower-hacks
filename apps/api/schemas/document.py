import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from apps.api.schemas.project import SensitivityStatus

_HASH = re.compile(r"^[0-9a-f]{64}$")


class ChunkCreate(BaseModel):
    chunk_index: int = Field(ge=0)
    text: str = Field(min_length=1, max_length=20000)
    embedding: list[float] | None = None
    fts_text: str | None = Field(default=None, max_length=20000)

    @field_validator("text")
    @classmethod
    def require_nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Chunk text must not be blank")
        return value


class ChunkBatchCreate(BaseModel):
    chunks: list[ChunkCreate] = Field(min_length=1)


class DocumentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    source_id: str = Field(min_length=1)
    title: str | None = Field(default=None, max_length=500)
    content_type: str | None = Field(default=None, max_length=200)
    raw_path: str | None = Field(default=None, max_length=2000)
    raw_text: str | None = Field(default=None, max_length=1_000_000)
    cleaned_text: str | None = Field(default=None, max_length=1_000_000)
    sensitivity_status: SensitivityStatus = SensitivityStatus.unreviewed
    content_hash: str | None = None
    chunks: list[ChunkCreate] = Field(default_factory=list)

    @field_validator("content_hash")
    @classmethod
    def normalize_hash(cls, value: str | None) -> str | None:
        if value is None:
            return None
        lowered = value.lower()
        if not _HASH.fullmatch(lowered):
            raise ValueError("content_hash must be a 64-character sha256 hex digest")
        return lowered

    @field_validator("title", "content_type", "raw_path", "raw_text", "cleaned_text")
    @classmethod
    def blank_optional_is_null(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value or None

    @model_validator(mode="after")
    def require_body(self) -> "DocumentCreate":
        if not self.cleaned_text and not self.raw_text:
            raise ValueError("cleaned_text or raw_text is required")
        return self


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    content_hash: str
    title: str | None
    content_type: str | None
    raw_path: str | None
    raw_text: str | None
    cleaned_text: str | None
    sensitivity_status: str
    created_at: str
    updated_at: str
    deduplicated: bool = False
    processing_metadata: dict[str, str] = Field(default_factory=dict)
    sensitivity_findings: list[dict[str, str]] = Field(default_factory=list)
    metadata_findings: list[dict[str, str]] = Field(default_factory=list)


class ChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    chunk_index: int
    text: str
    embedding: str | None
    fts_text: str
    created_at: str


class ChunkSearchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    source_id: str
    chunk_index: int
    text: str
