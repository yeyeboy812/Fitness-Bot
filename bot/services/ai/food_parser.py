"""AI-powered free-text food parser using OpenAI structured outputs."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from bot.integrations.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Ты — эксперт по нутрициологии. Пользователь описывает что он съел на русском языке.
Извлеки список продуктов с граммовками и КБЖУ на указанное количество.
Если граммовка не указана, используй стандартную порцию.
Если не уверен в продукте, предложи наиболее вероятный вариант.
Отвечай СТРОГО в формате JSON:
{
  "items": [
    {"name": "Название продукта", "amount_grams": 100, "calories": 100, "protein": 10, "fat": 5, "carbs": 15}
  ],
  "is_approximate": false
}
Поле is_approximate=true если расчёт примерный.\
"""


@dataclass
class ParsedFoodItem:
    name: str
    amount_grams: float
    calories: float
    protein: float
    fat: float
    carbs: float


@dataclass
class ParseResult:
    items: list[ParsedFoodItem]
    is_approximate: bool
    raw_response: dict | None = None


class AIFoodParserService:
    def __init__(self, client: OpenAIClient) -> None:
        self.client = client

    async def parse_text(self, text: str) -> ParseResult:
        """Parse free-text food description into structured items."""
        try:
            data = await self.client.chat_json(
                system_prompt=SYSTEM_PROMPT,
                user_message=text,
                model_type="text",
            )
            items = [
                ParsedFoodItem(
                    name=item["name"],
                    amount_grams=float(item["amount_grams"]),
                    calories=float(item["calories"]),
                    protein=float(item["protein"]),
                    fat=float(item["fat"]),
                    carbs=float(item["carbs"]),
                )
                for item in data.get("items", [])
            ]
            return ParseResult(
                items=items,
                is_approximate=data.get("is_approximate", True),
                raw_response=data,
            )
        except Exception:
            logger.exception("AI food parsing failed for: %s", text)
            return ParseResult(items=[], is_approximate=True)
