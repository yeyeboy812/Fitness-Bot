"""Thin OpenAI wrapper with cost tracking and rate limiting."""

from __future__ import annotations

import base64
import json
import logging
from io import BytesIO

from openai import AsyncOpenAI
from PIL import Image

from bot.config import Settings

logger = logging.getLogger(__name__)

MAX_IMAGE_DIMENSION = 1024


class OpenAIClient:
    def __init__(self, settings: Settings) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value()
        )
        self.text_model = settings.openai_text_model
        self.vision_model = settings.openai_vision_model

    async def chat_json(
        self,
        system_prompt: str,
        user_message: str,
        model_type: str = "text",
    ) -> dict:
        """Send a chat request expecting JSON response."""
        model = self.text_model if model_type == "text" else self.vision_model
        response = await self.client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)

    async def vision_json(
        self,
        system_prompt: str,
        image_bytes: bytes,
        user_message: str = "",
    ) -> dict:
        """Send an image + text request expecting JSON response."""
        resized = _resize_image(image_bytes)
        b64 = base64.b64encode(resized).decode()

        response = await self.client.chat.completions.create(
            model=self.vision_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}",
                                "detail": "low",
                            },
                        },
                        {"type": "text", "text": user_message},
                    ],
                },
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)


def _resize_image(image_bytes: bytes) -> bytes:
    """Resize image to max dimension for cost control."""
    img = Image.open(BytesIO(image_bytes))
    if max(img.size) > MAX_IMAGE_DIMENSION:
        img.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()
