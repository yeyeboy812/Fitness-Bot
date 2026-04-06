"""Analytics handler routers."""

from aiogram import Router

from .dashboard import router as dashboard_router

router = Router(name="analytics")
router.include_router(dashboard_router)
