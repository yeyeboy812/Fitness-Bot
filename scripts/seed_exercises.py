"""Seed the system catalog of exercises for every workout section.

Gym: 36 rows across 6 muscle groups. "Всё тело" has no dedicated rows —
it's a curated reference list stored in the handler.

Home / Warmup / Cooldown: rows for each name in the curated list that
isn't already covered by a gym canonical row. Some names (Подтягивания,
Планка, Скручивания, Подъём ног лёжа) are intentionally shared — the
home catalog just references the canonical gym row.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select

from bot.config import settings
from bot.models.base import create_db_engine, create_session_factory
from bot.models.exercise import (
    LOAD_BW_OPT_EXTRA,
    LOAD_EXTERNAL,
    LOAD_NO_WEIGHT,
    LOAD_TIME_ONLY,
    LOG_MODE_REPS,
    LOG_MODE_TIME,
    SECTION_COOLDOWN,
    SECTION_GYM,
    SECTION_HOME,
    SECTION_WARMUP,
    Exercise,
    ExerciseType,
    MuscleGroup,
)
from bot.repositories.exercise import normalize_exercise_name


# (name, muscle_group, exercise_type, log_mode, load_mode)
SeedRow = tuple[str, MuscleGroup, ExerciseType, str, str]

# --- GYM (36) ---
GYM_CHEST: list[SeedRow] = [
    ("Жим штанги лёжа", MuscleGroup.chest, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Жим гантелей лёжа", MuscleGroup.chest, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Жим на наклонной скамье", MuscleGroup.chest, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Разводка гантелей лёжа", MuscleGroup.chest, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Сведение рук в кроссовере", MuscleGroup.chest, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Отжимания на брусьях", MuscleGroup.chest, ExerciseType.bodyweight_reps, LOG_MODE_REPS, LOAD_BW_OPT_EXTRA),
]

GYM_BACK: list[SeedRow] = [
    ("Подтягивания", MuscleGroup.back, ExerciseType.bodyweight_reps, LOG_MODE_REPS, LOAD_BW_OPT_EXTRA),
    ("Тяга верхнего блока", MuscleGroup.back, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Тяга штанги в наклоне", MuscleGroup.back, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Тяга гантели к поясу", MuscleGroup.back, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Горизонтальная тяга блока", MuscleGroup.back, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Становая тяга", MuscleGroup.back, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
]

GYM_LEGS: list[SeedRow] = [
    ("Приседания со штангой", MuscleGroup.legs, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Жим ногами", MuscleGroup.legs, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Выпады с гантелями", MuscleGroup.legs, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Румынская тяга", MuscleGroup.legs, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Разгибание ног в тренажёре", MuscleGroup.legs, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Сгибание ног в тренажёре", MuscleGroup.legs, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
]

GYM_SHOULDERS: list[SeedRow] = [
    ("Жим гантелей сидя", MuscleGroup.shoulders, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Жим штанги стоя", MuscleGroup.shoulders, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Махи гантелями в стороны", MuscleGroup.shoulders, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Махи гантелями перед собой", MuscleGroup.shoulders, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Махи в наклоне на заднюю дельту", MuscleGroup.shoulders, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Тяга штанги к подбородку", MuscleGroup.shoulders, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
]

GYM_ARMS: list[SeedRow] = [
    ("Подъём штанги на бицепс", MuscleGroup.arms, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Молотки с гантелями", MuscleGroup.arms, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Концентрированный подъём на бицепс", MuscleGroup.arms, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Французский жим", MuscleGroup.arms, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Разгибание рук на блоке", MuscleGroup.arms, ExerciseType.weight_reps, LOG_MODE_REPS, LOAD_EXTERNAL),
    ("Отжимания узким хватом", MuscleGroup.arms, ExerciseType.bodyweight_reps, LOG_MODE_REPS, LOAD_BW_OPT_EXTRA),
]

GYM_ABS: list[SeedRow] = [
    ("Скручивания", MuscleGroup.abs, ExerciseType.bodyweight_reps, LOG_MODE_REPS, LOAD_NO_WEIGHT),
    ("Обратные скручивания", MuscleGroup.abs, ExerciseType.bodyweight_reps, LOG_MODE_REPS, LOAD_NO_WEIGHT),
    ("Подъём ног лёжа", MuscleGroup.abs, ExerciseType.bodyweight_reps, LOG_MODE_REPS, LOAD_NO_WEIGHT),
    ("Подъём ног в висе", MuscleGroup.abs, ExerciseType.bodyweight_reps, LOG_MODE_REPS, LOAD_BW_OPT_EXTRA),
    ("Велосипед", MuscleGroup.abs, ExerciseType.bodyweight_reps, LOG_MODE_REPS, LOAD_NO_WEIGHT),
    ("Планка", MuscleGroup.abs, ExerciseType.timed, LOG_MODE_TIME, LOAD_TIME_ONLY),
]

# --- HOME — only rows that aren't already canonical gym entries ---
HOME_ONLY: list[SeedRow] = [
    ("Отжимания", MuscleGroup.chest, ExerciseType.bodyweight_reps, LOG_MODE_REPS, LOAD_BW_OPT_EXTRA),
    ("Приседания", MuscleGroup.legs, ExerciseType.bodyweight_reps, LOG_MODE_REPS, LOAD_NO_WEIGHT),
    ("Берпи", MuscleGroup.cardio, ExerciseType.bodyweight_reps, LOG_MODE_REPS, LOAD_NO_WEIGHT),
    ("Обратные отжимания", MuscleGroup.arms, ExerciseType.bodyweight_reps, LOG_MODE_REPS, LOAD_BW_OPT_EXTRA),
    ("Выпады", MuscleGroup.legs, ExerciseType.bodyweight_reps, LOG_MODE_REPS, LOAD_NO_WEIGHT),
    ("Альпинист", MuscleGroup.cardio, ExerciseType.bodyweight_reps, LOG_MODE_REPS, LOAD_NO_WEIGHT),
]

# --- WARMUP ---
WARMUP_SEED: list[SeedRow] = [
    ("Прыжки на месте", MuscleGroup.cardio, ExerciseType.timed, LOG_MODE_TIME, LOAD_TIME_ONLY),
    ("Вращения руками", MuscleGroup.shoulders, ExerciseType.bodyweight_reps, LOG_MODE_REPS, LOAD_NO_WEIGHT),
    ("Махи руками", MuscleGroup.shoulders, ExerciseType.bodyweight_reps, LOG_MODE_REPS, LOAD_NO_WEIGHT),
    ("Приседания без веса", MuscleGroup.legs, ExerciseType.bodyweight_reps, LOG_MODE_REPS, LOAD_NO_WEIGHT),
    ("Выпады без веса", MuscleGroup.legs, ExerciseType.bodyweight_reps, LOG_MODE_REPS, LOAD_NO_WEIGHT),
    ("Суставная разминка", MuscleGroup.full_body, ExerciseType.timed, LOG_MODE_TIME, LOAD_TIME_ONLY),
    ("Бег на месте", MuscleGroup.cardio, ExerciseType.timed, LOG_MODE_TIME, LOAD_TIME_ONLY),
]

# --- COOLDOWN ---
COOLDOWN_SEED: list[SeedRow] = [
    ("Растяжка груди", MuscleGroup.chest, ExerciseType.timed, LOG_MODE_TIME, LOAD_TIME_ONLY),
    ("Растяжка спины", MuscleGroup.back, ExerciseType.timed, LOG_MODE_TIME, LOAD_TIME_ONLY),
    ("Растяжка ног", MuscleGroup.legs, ExerciseType.timed, LOG_MODE_TIME, LOAD_TIME_ONLY),
    ("Растяжка плеч", MuscleGroup.shoulders, ExerciseType.timed, LOG_MODE_TIME, LOAD_TIME_ONLY),
    ("Наклоны вперёд", MuscleGroup.full_body, ExerciseType.timed, LOG_MODE_TIME, LOAD_TIME_ONLY),
    ("Дыхательное восстановление", MuscleGroup.full_body, ExerciseType.timed, LOG_MODE_TIME, LOAD_TIME_ONLY),
    ("Ходьба", MuscleGroup.cardio, ExerciseType.timed, LOG_MODE_TIME, LOAD_TIME_ONLY),
    ("Растяжка всего тела", MuscleGroup.full_body, ExerciseType.timed, LOG_MODE_TIME, LOAD_TIME_ONLY),
]


SECTION_ROWS: list[tuple[str, list[SeedRow]]] = [
    (SECTION_GYM, GYM_CHEST + GYM_BACK + GYM_LEGS + GYM_SHOULDERS + GYM_ARMS + GYM_ABS),
    (SECTION_HOME, HOME_ONLY),
    (SECTION_WARMUP, WARMUP_SEED),
    (SECTION_COOLDOWN, COOLDOWN_SEED),
]


async def seed() -> None:
    engine = create_db_engine(settings.database_url)

    if "sqlite" in settings.database_url:
        from bot.models import Base  # noqa: F401
        from bot.models.base import create_tables
        await create_tables(engine)

    session_factory = create_session_factory(engine)

    inserted = 0
    skipped = 0
    async with session_factory() as session:
        for section, rows in SECTION_ROWS:
            for name, group, etype, log_mode, load_mode in rows:
                norm = normalize_exercise_name(name)
                existing = await session.scalar(
                    select(Exercise).where(
                        Exercise.user_id.is_(None),
                        func.lower(Exercise.name) == norm,
                    )
                )
                if existing:
                    # Make sure catalog metadata matches the seed source
                    # of truth (cheap, idempotent).
                    changed = False
                    if existing.section != section:
                        existing.section = section
                        changed = True
                    if existing.log_mode != log_mode:
                        existing.log_mode = log_mode
                        changed = True
                    if existing.load_mode != load_mode:
                        existing.load_mode = load_mode
                        changed = True
                    if existing.muscle_group != group:
                        existing.muscle_group = group
                        changed = True
                    if existing.exercise_type != etype:
                        existing.exercise_type = etype
                        changed = True
                    skipped += 1
                    if changed:
                        pass
                    continue
                session.add(Exercise(
                    name=name,
                    user_id=None,
                    muscle_group=group,
                    exercise_type=etype,
                    is_system=True,
                    section=section,
                    log_mode=log_mode,
                    load_mode=load_mode,
                ))
                inserted += 1
        await session.commit()

    await engine.dispose()
    print(f"Seeded {inserted} system exercises (updated/skipped {skipped} existing).")


if __name__ == "__main__":
    asyncio.run(seed())
