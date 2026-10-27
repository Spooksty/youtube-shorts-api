import base64
from pathlib import Path

import httpx

from app.config import settings
from app.integrations.base import ApiResult, MediaProvider, check_response

PROMPT = ("Vertical 9:16 photo for a short educational video. Subject: {keyword}. "
          "Context: {context}. Cinematic lighting, realistic, rich colors, no text, no captions, no watermarks.")


class OpenAIImages(MediaProvider):
    name = "OpenAI attēli"

    def find_clip(self, keyword: str, out_stem: Path, min_duration: float, context: str = "") -> ApiResult | None:
        resp = httpx.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_image_model,
                "prompt": PROMPT.format(keyword=keyword, context=context or keyword),
                "size": "1024x1536",
                "quality": settings.openai_image_quality,
                "n": 1,
            },
            timeout=180,
        )
        check_response(resp)
        out = out_stem.with_suffix(".png")
        out.write_bytes(base64.b64decode(resp.json()["data"][0]["b64_json"]))
        return ApiResult({"kind": "image", "path": out, "author": f"MI ģenerēts ({settings.openai_image_model})",
                          "source_url": None},
                         "openai", "images.generate", units=1, cost_eur=settings.openai_image_cost_eur)
