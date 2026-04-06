"""Nutrition handler routers."""

from aiogram import Router

from .add_meal import router as add_meal_router
from .daily_summary import router as daily_summary_router

router = Router(name="nutrition")
router.include_router(add_meal_router)
router.include_router(daily_summary_router)
