"""Product handler routers."""

from aiogram import Router

from .create import router as create_router
from .favorites import router as favorites_router

router = Router(name="products")
router.include_router(create_router)
router.include_router(favorites_router)
