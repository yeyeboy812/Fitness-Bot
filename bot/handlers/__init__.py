"""Register all handler routers on the dispatcher.

Router order matters — each router is checked in the order it is included.
``main_menu`` is intentionally registered first so that global navigation
buttons are always handled before any state-bound scenario handler. That
structural guarantee is what prevents menu text from being interpreted as
user input inside an active scenario.
"""

from aiogram import Dispatcher

from .admin import router as admin_router
from .analytics import router as analytics_router
from .common import router as common_router
from .main_menu import router as main_menu_router
from .nutrition import router as nutrition_router
from .onboarding import router as onboarding_router
from .products import router as products_router
from .recipes import router as recipes_router
from .workout import router as workout_router


def register_all_routers(dp: Dispatcher) -> None:
    # 1. Global menu navigation — highest priority.
    dp.include_router(main_menu_router)
    # 2. Global commands (/start, /help, /cancel).
    dp.include_router(common_router)
    # 3. Onboarding FSM (blocking flow until user.onboarding_completed).
    dp.include_router(onboarding_router)
    # 4. Feature scenarios.
    dp.include_router(nutrition_router)
    dp.include_router(workout_router)
    dp.include_router(recipes_router)
    dp.include_router(products_router)
    dp.include_router(analytics_router)
    # 5. Admin.
    dp.include_router(admin_router)
