"""ORM models — import all so Alembic can discover them."""

from .base import Base, TimestampMixin, create_db_engine, create_session_factory
from .agent import (
    AgentCommand,
    AgentCommandStatus,
    AgentCommandType,
    AgentEvent,
    AgentEventType,
    ShortcutActionType,
    UserShortcut,
)
from .exercise import Exercise, ExerciseType, MuscleGroup
from .meal import Meal, MealItem, MealItemSource, MealType
from .product import Product, ProductAlias, ProductSource
from .recipe import Recipe, RecipeIngredient
from .submission import Submission, SubmissionKind, SubmissionStatus
from .user import ActivityLevel, Gender, Goal, SubscriptionTier, User
from .workout import Workout, WorkoutExercise, WorkoutSet

__all__ = [
    "Base",
    "TimestampMixin",
    "create_db_engine",
    "create_session_factory",
    "AgentEvent",
    "AgentEventType",
    "AgentCommand",
    "AgentCommandType",
    "AgentCommandStatus",
    "UserShortcut",
    "ShortcutActionType",
    "User",
    "Gender",
    "Goal",
    "ActivityLevel",
    "SubscriptionTier",
    "Product",
    "ProductAlias",
    "ProductSource",
    "Meal",
    "MealItem",
    "MealType",
    "MealItemSource",
    "Recipe",
    "RecipeIngredient",
    "Submission",
    "SubmissionKind",
    "SubmissionStatus",
    "Exercise",
    "ExerciseType",
    "MuscleGroup",
    "Workout",
    "WorkoutExercise",
    "WorkoutSet",
]
