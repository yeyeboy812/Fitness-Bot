"""AI-powered food photo analysis using OpenAI Vision."""

from __future__ import annotations

import logging

from bot.integrations.openai_client import OpenAIClient
from bot.services.ai.food_parser import ParseResult, ParsedFoodItem

logger = logging.getLogger(__name__)

PHOTO_SYSTEM_PROMPT = """\
Ты — эксперт по нутрициологии. Проанализируй фото еды.
Определи все видимые продукты, оцени примерный вес каждого и рассчитай КБЖУ.
Если сомневаешься в продукте, укажи наиболее вероятный вариант.
Это ВСЕГДА приблизительная оценка — is_approximate=true.
Отвечай СТРОГО в формате JSON:
{
  "items": [
    {"name": "Название продукта", "amount_grams": 100, "calories": 100, "protein": 10, "fat": 5, "carbs": 15}
  ],
  "is_approximate": true
}\
"""


class AIPhotoAnalyzerService:
    def __init__(self, client: OpenAIClient) -> None:
        self.client = client

    async def analyze_photo(self, image_bytes: bytes) -> ParseResult:
        """Analyze food photo and return structured nutrition data."""
        try:
            data = await self.client.vision_json(
                system_prompt=PHOTO_SYSTEM_PROMPT,
                image_bytes=image_bytes,
                user_message="Что на этом фото? Рассчитай КБЖУ.",
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
                is_approximate=True,
                raw_response=data,
            )
        except Exception:
            logger.exception("AI photo analysis failed")
            return ParseResult(items=[], is_approximate=True)
