from pydantic import BaseModel, ConfigDict, Field


class InstagramProfileRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(min_length=1, max_length=30, pattern=r"^[A-Za-z0-9._]+$")


class InstagramProfileIngestRead(BaseModel):
    profile: "InstagramProfileRead"
    source_id: str
    document_id: str
    document_deduplicated: bool
    chunk_count: int


class InstagramPostRead(BaseModel):
    caption: str
    url: str | None
    timestamp: str | None
    likes_count: int | None
    comments_count: int | None


class InstagramProfileRead(BaseModel):
    username: str
    full_name: str | None
    biography: str | None
    profile_url: str | None
    profile_picture_url: str | None
    external_url: str | None
    category: str | None
    followers_count: int | None
    follows_count: int | None
    posts_count: int | None
    is_verified: bool | None
    is_private: bool | None
    recent_posts: list[InstagramPostRead]
