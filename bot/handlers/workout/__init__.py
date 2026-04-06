"""Workout handler routers."""

from aiogram import Router

from .start_workout import router as start_workout_router

router = Router(name="workout")
router.include_router(start_workout_router)
