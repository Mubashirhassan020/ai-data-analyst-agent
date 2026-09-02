"""ORM models. Every table listed in docs/architecture.md."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)

    datasets: Mapped[list[Dataset]] = relationship(back_populates="user")


class Dataset(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "datasets"

    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    parquet_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User | None] = relationship(back_populates="datasets")
    columns: Mapped[list[DatasetColumn]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    profile: Mapped[DatasetProfile | None] = relationship(
        back_populates="dataset", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (Index("ix_datasets_user_id", "user_id"),)


class DatasetColumn(UUIDMixin, Base):
    __tablename__ = "dataset_columns"

    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    inferred_type: Mapped[str] = mapped_column(String(32), nullable=False)
    logical_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    null_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unique_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    stats: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    dataset: Mapped[Dataset] = relationship(back_populates="columns")

    __table_args__ = (Index("ix_dataset_columns_dataset_id", "dataset_id"),)


class DatasetProfile(UUIDMixin, Base):
    __tablename__ = "dataset_profiles"

    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    quality_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    generated_at: Mapped[datetime | None] = mapped_column(nullable=True)

    dataset: Mapped[Dataset] = relationship(back_populates="profile")


class AnalysisSession(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "analysis_sessions"

    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    results: Mapped[list[AnalysisResult]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class AnalysisResult(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "analysis_results"

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    spec: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    session: Mapped[AnalysisSession] = relationship(back_populates="results")

    __table_args__ = (Index("ix_analysis_results_session_id", "session_id"),)


class ChatSession(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "chat_sessions"

    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "chat_messages"

    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user|assistant|tool
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tool_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tool_args: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    tool_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    session: Mapped[ChatSession] = relationship(back_populates="messages")

    __table_args__ = (Index("ix_chat_messages_session_id", "session_id"),)


class MLModel(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "ml_models"

    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    task: Mapped[str] = mapped_column(String(32), nullable=False)
    target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    features: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    algorithm: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    artifact_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")


class Report(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "reports"

    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    format: Mapped[str] = mapped_column(String(16), nullable=False)  # pdf|html|json
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    sections: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
