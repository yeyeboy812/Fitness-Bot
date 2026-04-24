"""Register context bot routers."""

from aiogram import Dispatcher

from .common import router as common_router
from .monitoring import router as monitoring_router


def register_all_routers(dp: Dispatcher) -> None:
    dp.include_router(common_router)
    dp.include_router(monitoring_router)
