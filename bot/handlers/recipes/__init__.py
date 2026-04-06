"""Recipe handler routers."""

from aiogram import Router

from .create import router as create_router
from .list_recipes import router as list_router

router = Router(name="recipes")
router.include_router(create_router)
router.include_router(list_router)
