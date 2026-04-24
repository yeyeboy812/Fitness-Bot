"""Repository for collector submissions."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.submission import Submission, SubmissionStatus

from .base import BaseRepository


class SubmissionRepository(BaseRepository[Submission]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Submission)

    async def list_pending(self, *, limit: int = 10) -> list[Submission]:
        stmt = (
            select(Submission)
            .where(Submission.status == SubmissionStatus.pending)
            .order_by(Submission.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def set_review(
        self,
        submission_id: UUID,
        *,
        status: SubmissionStatus,
        reviewed_by: int,
        review_comment: str | None = None,
        target_entity: str | None = None,
        target_entity_id: str | None = None,
    ) -> Submission:
        submission = await self.get_by_id(submission_id)
        if submission is None:
            raise ValueError(f"Submission {submission_id} not found")

        submission.status = status
        submission.reviewed_by = reviewed_by
        submission.review_comment = review_comment
        submission.target_entity = target_entity
        submission.target_entity_id = target_entity_id
        await self.session.flush()
        return submission
