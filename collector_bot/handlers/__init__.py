"""Register collector bot routers."""

from aiogram import Dispatcher

from .common import router as common_router
from .submit import router as submit_router


def register_all_routers(dp: Dispatcher) -> None:
    dp.include_router(common_router)
    dp.include_router(submit_router)
