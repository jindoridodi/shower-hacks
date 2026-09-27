from __future__ import annotations

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    sources: Mapped[list[Source]] = relationship(back_populates="project")
    reports: Mapped[list[Report]] = relationship(back_populates="project")


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "canonical_url",
            name="uq_sources_project_canonical_url",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    approval_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    is_allowlisted: Mapped[bool] = mapped_column(nullable=False, default=False)
    approved_at: Mapped[str | None] = mapped_column(String, nullable=True)
    approval_origin: Mapped[str | None] = mapped_column(String, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    scraped_at: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    project: Mapped[Project] = relationship(back_populates="sources")
    crawl_jobs: Mapped[list[CrawlJob]] = relationship(back_populates="source")
    documents: Mapped[list[Document]] = relationship(back_populates="source")
    claim_links: Mapped[list[ClaimSource]] = relationship(back_populates="source")
    approval: Mapped[SourceApproval | None] = relationship(back_populates="source")


class SourceApproval(Base):
    __tablename__ = "source_approvals"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str] = mapped_column(
        String, ForeignKey("sources.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    target_username: Mapped[str] = mapped_column(String, nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[str] = mapped_column(String, nullable=False)
    match_reason: Mapped[str] = mapped_column(Text, nullable=False)
    provider_evidence: Mapped[str] = mapped_column(Text, nullable=False)
    approved_at: Mapped[str] = mapped_column(String, nullable=False)

    source: Mapped[Source] = relationship(back_populates="approval")


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"
    __table_args__ = (
        Index(
            "uq_crawl_jobs_one_active",
            "source_id",
            unique=True,
            sqlite_where=text("status IN ('queued', 'running')"),
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str] = mapped_column(
        String, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[str | None] = mapped_column(String, nullable=True)
    completed_at: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    source: Mapped[Source] = relationship(back_populates="crawl_jobs")


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("source_id", "content_hash", name="uq_documents_source_hash"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str] = mapped_column(
        String, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cleaned_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sensitivity_status: Mapped[str] = mapped_column(
        String, nullable=False, default="unreviewed"
    )
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    processing_metadata: Mapped[dict[str, str]] = mapped_column(
        JSON, nullable=False, default=dict, server_default=text("'{}'")
    )
    sensitivity_findings: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, nullable=False, default=list, server_default=text("'[]'")
    )
    metadata_findings: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, nullable=False, default=list, server_default=text("'[]'")
    )

    source: Mapped[Source] = relationship(back_populates="documents")
    chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="document",
        order_by="DocumentChunk.chunk_index",
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_chunks_document_index"),
        CheckConstraint("chunk_index >= 0", name="ck_chunks_index_nonnegative"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    fts_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[str] = mapped_column(String, nullable=False)

    document: Mapped[Document] = relationship(back_populates="chunks")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    project: Mapped[Project] = relationship(back_populates="reports")
    claims: Mapped[list[ReportClaim]] = relationship(
        back_populates="report",
        order_by="ReportClaim.position",
    )


class ReportClaim(Base):
    __tablename__ = "report_claims"
    __table_args__ = (
        UniqueConstraint(
            "report_id",
            "position",
            name="uq_report_claims_report_position",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    report_id: Mapped[str] = mapped_column(
        String, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String, nullable=False)

    report: Mapped[Report] = relationship(back_populates="claims")
    sources: Mapped[list[ClaimSource]] = relationship(
        back_populates="claim",
        order_by="ClaimSource.created_at",
    )


class ClaimSource(Base):
    __tablename__ = "claim_sources"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    claim_id: Mapped[str] = mapped_column(
        String, ForeignKey("report_claims.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[str] = mapped_column(
        String, ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)

    claim: Mapped[ReportClaim] = relationship(back_populates="sources")
    source: Mapped[Source] = relationship(back_populates="claim_links")
