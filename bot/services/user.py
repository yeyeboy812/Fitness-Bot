"""User service — profile management and norm calculation."""

from datetime import date

from bot.models.user import User
from bot.repositories.user import UserRepository
from bot.schemas.user import OnboardingData
from bot.services.calorie_calc import (
    ActivityLevel,
    Gender,
    Goal,
    calculate_norms,
)


def is_profile_complete(user: User) -> bool:
    """Return True when the user can safely skip onboarding.

    ``onboarding_completed`` is the canonical flag. The field check is a
    compatibility fallback for existing rows that already have profile data
    but were created before the flag was set correctly.
    """
    if user.onboarding_completed:
        return True

    required_fields = (
        user.first_name,
        user.gender,
        user.birth_year,
        user.height_cm,
        user.weight_kg,
        user.goal,
        user.activity_level,
        user.calorie_norm,
        user.protein_norm,
        user.fat_norm,
        user.carb_norm,
    )
    return all(value is not None for value in required_fields)


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def get_or_create(
        self, telegram_id: int, first_name: str, username: str | None = None
    ) -> tuple[User, bool]:
        return await self.repo.get_or_create(telegram_id, first_name, username)

    async def complete_onboarding(self, user_id: int, data: OnboardingData) -> User:
        age = date.today().year - data.birth_year
        norms = calculate_norms(
            gender=Gender(data.gender.value),
            weight_kg=data.weight_kg,
            height_cm=data.height_cm,
            age=age,
            activity_level=ActivityLevel(data.activity_level.value),
            goal=Goal(data.goal.value),
        )

        user = await self.repo.update_profile(
            user_id,
            first_name=data.first_name,
            gender=data.gender.value,
            birth_year=data.birth_year,
            height_cm=data.height_cm,
            weight_kg=data.weight_kg,
            goal=data.goal.value,
            activity_level=data.activity_level.value,
            referral_source=data.referral_source,
            calorie_norm=norms.calories,
            protein_norm=norms.protein_g,
            fat_norm=norms.fat_g,
            carb_norm=norms.carbs_g,
            onboarding_completed=True,
        )
        return user

    async def is_onboarded(self, user_id: int) -> bool:
        user = await self.repo.get_by_id(user_id)
        return user is not None and is_profile_complete(user)

    async def update_profile_field(self, user_id: int, field: str, value: object) -> User:
        if field not in {
            "first_name",
            "gender",
            "birth_year",
            "weight_kg",
            "height_cm",
            "goal",
            "activity_level",
        }:
            raise ValueError(f"Unsupported profile field: {field}")

        user = await self.repo.update_profile(user_id, **{field: value})
        if field != "first_name" and self._can_recalculate_norms(user):
            return await self.recalculate_norms(user_id)
        return user

    async def recalculate_norms(self, user_id: int) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user or not self._can_recalculate_norms(user):
            raise ValueError("Incomplete profile")

        age = date.today().year - user.birth_year
        norms = calculate_norms(
            gender=Gender(_enum_value(user.gender)),
            weight_kg=user.weight_kg,
            height_cm=user.height_cm,
            age=age,
            activity_level=ActivityLevel(_enum_value(user.activity_level)),
            goal=Goal(_enum_value(user.goal)),
        )
        return await self.repo.update_profile(
            user_id,
            calorie_norm=norms.calories,
            protein_norm=norms.protein_g,
            fat_norm=norms.fat_g,
            carb_norm=norms.carbs_g,
        )

    @staticmethod
    def _can_recalculate_norms(user: User) -> bool:
        return all(
            [
                user.gender,
                user.birth_year,
                user.height_cm,
                user.weight_kg,
                user.goal,
                user.activity_level,
            ]
        )


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)
