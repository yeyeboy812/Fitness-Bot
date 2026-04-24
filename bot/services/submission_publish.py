"""Publish approved collector submissions into the main bot tables."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.exercise import Exercise, ExerciseType, MuscleGroup
from bot.models.product import Product, ProductSource
from bot.models.recipe import Recipe
from bot.models.submission import Submission, SubmissionKind
from bot.repositories.base import BaseRepository


async def publish_submission(
    session: AsyncSession,
    submission: Submission,
) -> tuple[str, str]:
    """Create the target entity in the shared DB and return its kind/id.

    If an identical record was already published earlier, reuse it instead of
    inserting a duplicate row.
    """
    payload = submission.payload

    if submission.kind == SubmissionKind.exercise:
        existing = await _find_existing_exercise(session, payload)
        if existing is not None:
            return "exercise", str(existing.id)

        repo = BaseRepository(session, Exercise)
        entity = await repo.create(
            user_id=None,
            name=payload["name"],
            muscle_group=MuscleGroup(payload["muscle_group"]),
            exercise_type=ExerciseType(payload["exercise_type"]),
            is_system=True,
        )
        return "exercise", str(entity.id)

    if submission.kind == SubmissionKind.product:
        existing = await _find_existing_product(session, payload)
        if existing is not None:
            return "product", str(existing.id)

        repo = BaseRepository(session, Product)
        entity = await repo.create(
            user_id=None,
            name=payload["name"],
            brand=payload.get("brand") or None,
            calories_per_100g=payload["calories_per_100g"],
            protein_per_100g=payload["protein_per_100g"],
            fat_per_100g=payload["fat_per_100g"],
            carbs_per_100g=payload["carbs_per_100g"],
            is_verified=True,
            source=ProductSource.system,
        )
        return "product", str(entity.id)

    if submission.kind == SubmissionKind.recipe:
        existing = await _find_existing_recipe(session, submission.telegram_user_id, payload)
        if existing is not None:
            return "recipe", str(existing.id)

        repo = BaseRepository(session, Recipe)
        entity = await repo.create(
            user_id=submission.telegram_user_id,
            name=payload["name"],
            total_weight_grams=payload["total_weight_grams"],
            servings=payload["servings"],
            calories_per_100g=payload["calories_per_100g"],
            protein_per_100g=payload["protein_per_100g"],
            fat_per_100g=payload["fat_per_100g"],
            carbs_per_100g=payload["carbs_per_100g"],
        )
        return "recipe", str(entity.id)

    raise ValueError(f"Unsupported submission kind: {submission.kind}")


async def _find_existing_exercise(
    session: AsyncSession,
    payload: dict[str, str | int | float],
) -> Exercise | None:
    stmt = select(Exercise).where(
        Exercise.user_id.is_(None),
        Exercise.is_system.is_(True),
        Exercise.name == payload["name"],
        Exercise.muscle_group == MuscleGroup(payload["muscle_group"]),
        Exercise.exercise_type == ExerciseType(payload["exercise_type"]),
    )
    return await session.scalar(stmt)


async def _find_existing_product(
    session: AsyncSession,
    payload: dict[str, str | int | float],
) -> Product | None:
    stmt = select(Product).where(
        Product.user_id.is_(None),
        Product.name == payload["name"],
        Product.brand == (payload.get("brand") or None),
        Product.calories_per_100g == payload["calories_per_100g"],
        Product.protein_per_100g == payload["protein_per_100g"],
        Product.fat_per_100g == payload["fat_per_100g"],
        Product.carbs_per_100g == payload["carbs_per_100g"],
    )
    return await session.scalar(stmt)


async def _find_existing_recipe(
    session: AsyncSession,
    user_id: int,
    payload: dict[str, str | int | float],
) -> Recipe | None:
    stmt = select(Recipe).where(
        Recipe.user_id == user_id,
        Recipe.name == payload["name"],
        Recipe.total_weight_grams == payload["total_weight_grams"],
        Recipe.servings == payload["servings"],
        Recipe.calories_per_100g == payload["calories_per_100g"],
        Recipe.protein_per_100g == payload["protein_per_100g"],
        Recipe.fat_per_100g == payload["fat_per_100g"],
        Recipe.carbs_per_100g == payload["carbs_per_100g"],
    )
    return await session.scalar(stmt)
