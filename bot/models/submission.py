"""Collector-bot submissions stored in the shared database."""

from __future__ import annotations

import enum
import uuid
from typing import Any

from sqlalchemy import BigInteger, JSON, String, Text, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class SubmissionKind(enum.Enum):
    product = "product"
    recipe = "recipe"
    exercise = "exercise"


class SubmissionStatus(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Submission(TimestampMixin, Base):
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    kind: Mapped[SubmissionKind] = mapped_column(
        SAEnum(SubmissionKind, name="submission_kind_enum"),
        nullable=False,
    )
    status: Mapped[SubmissionStatus] = mapped_column(
        SAEnum(SubmissionStatus, name="submission_status_enum"),
        default=SubmissionStatus.pending,
        server_default="pending",
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    source_bot: Mapped[str] = mapped_column(
        String(32),
        default="collector",
        server_default="collector",
        nullable=False,
    )
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    target_entity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Submission {self.kind.value}:{self.status.value} {self.title!r}>"
