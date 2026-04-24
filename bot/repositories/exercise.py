"""Exercise repository."""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.exercise import (
    LOAD_EXTERNAL,
    LOG_MODE_REPS,
    SECTION_GYM,
    Exercise,
    ExerciseType,
    MuscleGroup,
)

from .base import BaseRepository

# Legacy aliases: UI "Руки" maps to arms, but older rows may live under the
# deprecated biceps/triceps enum values. Include them when querying arms so
# personal exercises saved before the catalog rework stay visible.
_MUSCLE_GROUP_ALIASES: dict[MuscleGroup, tuple[MuscleGroup, ...]] = {
    MuscleGroup.arms: (MuscleGroup.arms, MuscleGroup.biceps, MuscleGroup.triceps),
}


def _expand_groups(group: MuscleGroup) -> tuple[MuscleGroup, ...]:
    return _MUSCLE_GROUP_ALIASES.get(group, (group,))


def normalize_exercise_name(name: str) -> str:
    """Canonical form for name matching: lowercased, ё→е, whitespace squashed.

    Used both for Full-Body reuse ("Жим штанги стоя" entered by user must
    resolve to the existing canonical "shoulders" row) and for personal
    exercise deduplication.
    """
    return " ".join(name.strip().lower().replace("ё", "е").split())


class ExerciseRepository(BaseRepository[Exercise]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Exercise)

    async def search(
        self,
        query: str,
        user_id: int | None = None,
        limit: int = 10,
    ) -> list[Exercise]:
        pattern = f"%{query}%"
        stmt = (
            select(Exercise)
            .where(
                Exercise.name.ilike(pattern),
                or_(Exercise.user_id.is_(None), Exercise.user_id == user_id),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_muscle_group(
        self,
        muscle_group: MuscleGroup,
        user_id: int,
        limit: int,
        offset: int,
    ) -> list[Exercise]:
        """Gym-section exercises in a muscle group. Global first, then personal.

        Filters by section='gym' — the gym flow must not surface rows seeded
        for home/warmup/cooldown (e.g. bodyweight-only "Приседания") as if
        they were gym canonicals.
        """
        groups = _expand_groups(muscle_group)
        is_personal = Exercise.user_id.isnot(None)
        stmt = (
            select(Exercise)
            .where(
                Exercise.muscle_group.in_(groups),
                Exercise.section == SECTION_GYM,
                or_(Exercise.user_id.is_(None), Exercise.user_id == user_id),
            )
            .order_by(is_personal.asc(), Exercise.name.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_muscle_group(
        self,
        muscle_group: MuscleGroup,
        user_id: int,
    ) -> int:
        groups = _expand_groups(muscle_group)
        stmt = (
            select(func.count())
            .select_from(Exercise)
            .where(
                Exercise.muscle_group.in_(groups),
                Exercise.section == SECTION_GYM,
                or_(Exercise.user_id.is_(None), Exercise.user_id == user_id),
            )
        )
        return await self.session.scalar(stmt) or 0

    async def find_by_name(
        self,
        name: str,
        user_id: int,
    ) -> Exercise | None:
        """Visible-to-user exercise whose normalized name equals *name*.

        Matches on Python side via ``normalize_exercise_name`` — SQLite's
        ``LOWER()`` is ASCII-only and silently breaks Cyrillic compare.
        Canonical row (``user_id IS NULL``) wins over a personal duplicate
        so a user-created row never hides the canonical one.
        """
        norm = normalize_exercise_name(name)
        if not norm:
            return None
        stmt = select(Exercise).where(
            or_(Exercise.user_id.is_(None), Exercise.user_id == user_id),
        )
        result = await self.session.execute(stmt)
        personal_hit: Exercise | None = None
        for ex in result.scalars():
            if normalize_exercise_name(ex.name) != norm:
                continue
            if ex.user_id is None:
                return ex
            personal_hit = personal_hit or ex
        return personal_hit

    async def list_by_names(
        self,
        names: list[str],
        user_id: int,
    ) -> list[Exercise]:
        """Resolve an ordered curated list of names to canonical Exercise rows.

        Matches on Python side via ``normalize_exercise_name`` — avoids the
        SQLite ``LOWER()`` ASCII-only limitation that breaks Cyrillic
        case-insensitive compare. Canonical rows win over personal duplicates.
        Preserves input order; silently drops names with no match.
        """
        if not names:
            return []
        stmt = select(Exercise).where(
            or_(Exercise.user_id.is_(None), Exercise.user_id == user_id),
        )
        result = await self.session.execute(stmt)
        by_norm: dict[str, Exercise] = {}
        for ex in result.scalars():
            key = normalize_exercise_name(ex.name)
            # Canonical (user_id is None) takes precedence over personal.
            existing = by_norm.get(key)
            if existing is None or (
                existing.user_id is not None and ex.user_id is None
            ):
                by_norm[key] = ex
        out: list[Exercise] = []
        for name in names:
            ex = by_norm.get(normalize_exercise_name(name))
            if ex is not None:
                out.append(ex)
        return out

    async def create_personal(
        self,
        name: str,
        user_id: int,
        muscle_group: MuscleGroup,
        exercise_type: ExerciseType = ExerciseType.weight_reps,
        *,
        section: str = SECTION_GYM,
        log_mode: str = LOG_MODE_REPS,
        load_mode: str = LOAD_EXTERNAL,
    ) -> Exercise:
        return await self.create(
            name=name,
            user_id=user_id,
            muscle_group=muscle_group,
            exercise_type=exercise_type,
            section=section,
            log_mode=log_mode,
            load_mode=load_mode,
        )

    async def get_or_create_user_exercise(
        self,
        name: str,
        user_id: int,
        muscle_group: MuscleGroup = MuscleGroup.other,
        exercise_type: ExerciseType = ExerciseType.weight_reps,
        *,
        section: str = SECTION_GYM,
        log_mode: str = LOG_MODE_REPS,
        load_mode: str = LOAD_EXTERNAL,
    ) -> tuple[Exercise, bool]:
        """Get existing or create a new user exercise.

        Uses normalized-name lookup so unicode variants ("лёжа" vs "лежа")
        deduplicate correctly.
        """
        existing = await self.find_by_name(name, user_id=user_id)
        if existing is not None:
            return existing, False

        exercise = await self.create(
            name=name,
            user_id=user_id,
            muscle_group=muscle_group,
            exercise_type=exercise_type,
            section=section,
            log_mode=log_mode,
            load_mode=load_mode,
        )
        return exercise, True
